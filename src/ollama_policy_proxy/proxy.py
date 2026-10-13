from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Mapping
from http import HTTPStatus

import aiohttp
from aiohttp import web
from multidict import CIMultiDict

from .config import ProxyConfig
from .policy import UnknownProfileError, apply_policy

LOGGER = logging.getLogger("ollama_policy_proxy")
PROFILE_HEADER = "X-Ollama-Profile"
POLICY_ENDPOINTS = {"/api/chat", "/api/generate"}
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
SESSION_KEY: web.AppKey[aiohttp.ClientSession] = web.AppKey("upstream_session")
CONFIG_KEY: web.AppKey[ProxyConfig] = web.AppKey("config")


def create_app(config: ProxyConfig) -> web.Application:
    app = web.Application(client_max_size=config.server.max_policy_body_bytes)
    app[CONFIG_KEY] = config
    app.cleanup_ctx.append(_client_session)
    app.router.add_route("*", "/{path_info:.*}", _proxy_request)
    return app


async def _client_session(app: web.Application) -> AsyncIterator[None]:
    config = app[CONFIG_KEY]
    timeout = aiohttp.ClientTimeout(
        total=None,
        sock_connect=config.upstream.connect_timeout,
        sock_read=config.upstream.read_timeout,
    )
    async with aiohttp.ClientSession(timeout=timeout, auto_decompress=False) as session:
        app[SESSION_KEY] = session
        yield


async def _proxy_request(request: web.Request) -> web.StreamResponse:
    config = request.app[CONFIG_KEY]
    profile = request.headers.get(PROFILE_HEADER)
    transformed = request.method == "POST" and request.path in POLICY_ENDPOINTS

    if profile is not None and profile not in config.profiles:
        return _json_error(HTTPStatus.BAD_REQUEST, f"unknown inference profile: {profile}")

    try:
        body, model = await _request_body(request, config, profile, transformed)
    except web.HTTPRequestEntityTooLarge:
        return _json_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body is too large")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _json_error(HTTPStatus.BAD_REQUEST, "request body must be valid JSON")
    except ValueError as error:
        return _json_error(HTTPStatus.BAD_REQUEST, str(error))

    headers = _forward_headers(request.headers, transformed=transformed, response=False)
    if transformed:
        headers["Content-Type"] = "application/json"

    upstream_url = f"{config.upstream.url}{request.raw_path}"
    LOGGER.info(
        "%s %s model=%s profile=%s",
        request.method,
        request.path,
        model or "-",
        profile or "-",
    )

    try:
        upstream = await request.app[SESSION_KEY].request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            data=body,
            allow_redirects=False,
        )
    except (aiohttp.ClientConnectorError, aiohttp.ConnectionTimeoutError):
        return _json_error(HTTPStatus.BAD_GATEWAY, "could not connect to upstream Ollama")
    except TimeoutError:
        return _json_error(HTTPStatus.GATEWAY_TIMEOUT, "upstream Ollama request timed out")
    except aiohttp.ClientError:
        return _json_error(HTTPStatus.BAD_GATEWAY, "could not connect to upstream Ollama")

    try:
        response_headers = _forward_headers(upstream.headers, transformed=False, response=True)
        response = web.StreamResponse(
            status=upstream.status,
            reason=upstream.reason,
            headers=response_headers,
        )
        await response.prepare(request)
        async for chunk in upstream.content.iter_any():
            await response.write(chunk)
        await response.write_eof()
        return response
    except (ConnectionResetError, asyncio.CancelledError):
        upstream.close()
        raise
    except aiohttp.ClientError:
        response.force_close()
        return response
    finally:
        upstream.release()


async def _request_body(
    request: web.Request,
    config: ProxyConfig,
    profile: str | None,
    transformed: bool,
) -> tuple[bytes | aiohttp.StreamReader, str | None]:
    if not transformed:
        return request.content, None

    raw_body = await request.read()
    document = json.loads(raw_body)
    if not isinstance(document, dict):
        raise ValueError("request body must be a JSON object")
    try:
        transformed_body = apply_policy(document, config, profile)
    except UnknownProfileError as error:
        raise ValueError(f"unknown inference profile: {error.args[0]}") from error
    model = document.get("model")
    encoded = json.dumps(transformed_body, separators=(",", ":"), ensure_ascii=False).encode()
    return encoded, model if isinstance(model, str) else None


def _forward_headers(
    headers: Mapping[str, str],
    *,
    transformed: bool,
    response: bool,
) -> CIMultiDict[str]:
    source = CIMultiDict(headers)
    connection_tokens = {
        token.strip().lower()
        for value in source.getall("Connection", [])
        for token in value.split(",")
        if token.strip()
    }
    excluded = HOP_BY_HOP_HEADERS | connection_tokens | {PROFILE_HEADER.lower()}
    if not response:
        excluded.add("host")
    if transformed or response:
        excluded.add("content-length")

    result: CIMultiDict[str] = CIMultiDict()
    for name, value in source.items():
        if name.lower() not in excluded:
            result.add(name, value)
    return result


def _json_error(status: HTTPStatus, message: str) -> web.Response:
    return web.json_response({"error": message}, status=int(status))
