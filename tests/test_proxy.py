from __future__ import annotations

import asyncio
import json
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiohttp
import pytest
from aiohttp import web

from ollama_policy_proxy.config import ProxyConfig, parse_config
from ollama_policy_proxy.proxy import create_app

FIXTURES = Path(__file__).parent / "fixtures"


@asynccontextmanager
async def running_app(app: web.Application) -> AsyncIterator[str]:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    sockets = site._server.sockets
    port = sockets[0].getsockname()[1]
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        await runner.cleanup()


def config_for(upstream_url: str, **upstream_values: object) -> ProxyConfig:
    return parse_config(
        {
            "upstream": {"url": upstream_url, **upstream_values},
            "defaults": {"think": False, "options": {"num_predict": 2048}},
            "models": {"qwen3:8b": {"options": {"temperature": 0.2}}},
            "profiles": {"fast": {"options": {"num_predict": 256}}},
        }
    )


@pytest.mark.asyncio
async def test_transformed_request_preserves_ollama_payload_and_strips_proxy_header() -> None:
    captured: dict[str, object] = {}

    async def upstream(request: web.Request) -> web.Response:
        captured["body"] = await request.json()
        captured["headers"] = dict(request.headers)
        return web.json_response({"done": True})

    upstream_app = web.Application()
    upstream_app.router.add_post("/api/chat", upstream)
    async with running_app(upstream_app) as upstream_url:
        async with running_app(create_app(config_for(upstream_url))) as proxy_url:
            body = json.loads((FIXTURES / "chat_request.json").read_text(encoding="utf-8"))
            async with aiohttp.ClientSession() as client:
                async with client.post(
                    f"{proxy_url}/api/chat",
                    json=body,
                    headers={"X-Ollama-Profile": "fast", "X-Trace": "kept"},
                ) as response:
                    assert response.status == 200

    forwarded = captured["body"]
    assert forwarded["messages"] == body["messages"]
    assert forwarded["tools"] == body["tools"]
    assert forwarded["format"] == body["format"]
    assert forwarded["think"] is False
    assert forwarded["options"] == {"num_predict": 256, "temperature": 0.2}
    assert captured["headers"]["X-Trace"] == "kept"
    assert "X-Ollama-Profile" not in captured["headers"]


@pytest.mark.asyncio
async def test_unknown_profile_is_rejected_without_upstream_request() -> None:
    called = False

    async def upstream(request: web.Request) -> web.Response:
        nonlocal called
        called = True
        return web.Response()

    upstream_app = web.Application()
    upstream_app.router.add_route("*", "/{tail:.*}", upstream)
    async with running_app(upstream_app) as upstream_url:
        async with running_app(create_app(config_for(upstream_url))) as proxy_url:
            async with aiohttp.ClientSession() as client:
                async with client.post(
                    f"{proxy_url}/api/generate",
                    json={"model": "qwen3:8b", "prompt": "hello"},
                    headers={"X-Ollama-Profile": "missing"},
                ) as response:
                    assert response.status == 400
                    assert await response.json() == {"error": "unknown inference profile: missing"}
    assert called is False


@pytest.mark.asyncio
async def test_invalid_client_json_is_rejected() -> None:
    upstream_app = web.Application()
    async with running_app(upstream_app) as upstream_url:
        async with running_app(create_app(config_for(upstream_url))) as proxy_url:
            async with aiohttp.ClientSession() as client:
                async with client.post(
                    f"{proxy_url}/api/chat",
                    data=b"not-json",
                    headers={"Content-Type": "application/json"},
                ) as response:
                    assert response.status == 400
                    assert await response.json() == {"error": "request body must be valid JSON"}


@pytest.mark.asyncio
async def test_pass_through_request_is_unmodified() -> None:
    captured: dict[str, object] = {}
    payload = b"\x00binary\xffpayload"

    async def upstream(request: web.Request) -> web.Response:
        captured["method"] = request.method
        captured["path"] = request.raw_path
        captured["body"] = await request.read()
        captured["content_type"] = request.headers.get("Content-Type")
        return web.Response(body=b"upstream", status=201, headers={"X-Upstream": "yes"})

    upstream_app = web.Application()
    upstream_app.router.add_route("*", "/{tail:.*}", upstream)
    async with running_app(upstream_app) as upstream_url:
        async with running_app(create_app(config_for(upstream_url))) as proxy_url:
            async with aiohttp.ClientSession() as client:
                async with client.put(
                    f"{proxy_url}/api/custom?value=1",
                    data=payload,
                    headers={"Content-Type": "application/octet-stream"},
                ) as response:
                    assert response.status == 201
                    assert response.headers["X-Upstream"] == "yes"
                    assert await response.read() == b"upstream"

    assert captured == {
        "method": "PUT",
        "path": "/api/custom?value=1",
        "body": payload,
        "content_type": "application/octet-stream",
    }


@pytest.mark.asyncio
async def test_streaming_response_is_incremental_and_complete() -> None:
    first_written = asyncio.Event()
    release_rest = asyncio.Event()
    lines = (FIXTURES / "stream.ndjson").read_bytes().splitlines(keepends=True)

    async def upstream(request: web.Request) -> web.StreamResponse:
        response = web.StreamResponse(headers={"Content-Type": "application/x-ndjson"})
        await response.prepare(request)
        await response.write(lines[0])
        first_written.set()
        await release_rest.wait()
        for line in lines[1:]:
            await response.write(line)
        return response

    upstream_app = web.Application()
    upstream_app.router.add_post("/api/generate", upstream)
    async with running_app(upstream_app) as upstream_url:
        async with running_app(create_app(config_for(upstream_url))) as proxy_url:
            async with aiohttp.ClientSession() as client:
                response = await client.post(
                    f"{proxy_url}/api/generate",
                    json={"model": "qwen3:8b", "prompt": "hello"},
                )
                await asyncio.wait_for(first_written.wait(), 1)
                first_chunk = await asyncio.wait_for(response.content.readline(), 1)
                assert first_chunk == lines[0]
                assert response.content.at_eof() is False
                release_rest.set()
                assert first_chunk + await response.read() == b"".join(lines)


@pytest.mark.asyncio
async def test_upstream_http_error_is_preserved() -> None:
    async def upstream(request: web.Request) -> web.Response:
        return web.json_response({"error": "model not found"}, status=404)

    upstream_app = web.Application()
    upstream_app.router.add_post("/api/show", upstream)
    async with running_app(upstream_app) as upstream_url:
        async with running_app(create_app(config_for(upstream_url))) as proxy_url:
            async with aiohttp.ClientSession() as client:
                async with client.post(
                    f"{proxy_url}/api/show", json={"model": "missing"}
                ) as response:
                    assert response.status == 404
                    assert await response.json() == {"error": "model not found"}


@pytest.mark.asyncio
async def test_upstream_disconnect_ends_partial_stream_without_buffering() -> None:
    first_line = b'{"response":"partial","done":false}\n'

    async def upstream(request: web.Request) -> web.StreamResponse:
        response = web.StreamResponse(headers={"Content-Type": "application/x-ndjson"})
        await response.prepare(request)
        await response.write(first_line)
        request.transport.close()
        return response

    upstream_app = web.Application()
    upstream_app.router.add_post("/api/generate", upstream)
    async with running_app(upstream_app) as upstream_url:
        async with running_app(create_app(config_for(upstream_url))) as proxy_url:
            async with aiohttp.ClientSession() as client:
                response = await client.post(
                    f"{proxy_url}/api/generate",
                    json={"model": "qwen3:8b", "prompt": "hello"},
                )
                assert response.status == 200
                assert await asyncio.wait_for(response.content.readline(), 1) == first_line
                assert await asyncio.wait_for(response.content.read(), 1) == b""


@pytest.mark.asyncio
async def test_upstream_timeout_returns_gateway_timeout() -> None:
    async def upstream(request: web.Request) -> web.Response:
        await asyncio.sleep(0.2)
        return web.Response()

    upstream_app = web.Application()
    upstream_app.router.add_get("/api/tags", upstream)
    async with running_app(upstream_app) as upstream_url:
        config = config_for(upstream_url, read_timeout=0.05)
        async with running_app(create_app(config)) as proxy_url:
            async with aiohttp.ClientSession() as client:
                async with client.get(f"{proxy_url}/api/tags") as response:
                    assert response.status == 504
                    assert await response.json() == {"error": "upstream Ollama request timed out"}


@pytest.mark.asyncio
async def test_upstream_connection_failure_returns_bad_gateway() -> None:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        unused_port = sock.getsockname()[1]

    config = config_for(f"http://127.0.0.1:{unused_port}", connect_timeout=0.1)
    async with running_app(create_app(config)) as proxy_url:
        async with aiohttp.ClientSession() as client:
            async with client.get(f"{proxy_url}/api/tags") as response:
                assert response.status == 502
                assert await response.json() == {"error": "could not connect to upstream Ollama"}


@pytest.mark.asyncio
async def test_client_cancellation_closes_upstream_connection() -> None:
    upstream_connected = asyncio.Event()
    upstream_cleaned = asyncio.Event()

    async def upstream(request: web.Request) -> web.StreamResponse:
        response = web.StreamResponse(headers={"Content-Type": "application/x-ndjson"})
        await response.prepare(request)
        upstream_connected.set()
        try:
            while True:
                await response.write(b'{"done":false}\n')
                await asyncio.sleep(0.01)
        except ConnectionResetError:
            upstream_cleaned.set()
        return response

    upstream_app = web.Application()
    upstream_app.router.add_post("/api/generate", upstream)
    async with running_app(upstream_app) as upstream_url:
        async with running_app(create_app(config_for(upstream_url))) as proxy_url:
            async with aiohttp.ClientSession() as client:
                response = await client.post(
                    f"{proxy_url}/api/generate",
                    json={"model": "qwen3:8b", "prompt": "hello"},
                )
                await asyncio.wait_for(upstream_connected.wait(), 1)
                await response.content.readline()
                response.close()
                await asyncio.wait_for(upstream_cleaned.wait(), 2)
