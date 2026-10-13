from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml


class ConfigError(ValueError):
    """Raised when the proxy configuration is invalid."""


Policy = dict[str, Any]


@dataclass(frozen=True, slots=True)
class UpstreamConfig:
    url: str
    connect_timeout: float = 10.0
    read_timeout: float = 300.0


@dataclass(frozen=True, slots=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 11435
    max_policy_body_bytes: int = 64 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ProxyConfig:
    upstream: UpstreamConfig
    server: ServerConfig = field(default_factory=ServerConfig)
    defaults: Policy = field(default_factory=dict)
    models: dict[str, Policy] = field(default_factory=dict)
    profiles: dict[str, Policy] = field(default_factory=dict)


def load_config(path: str | Path) -> ProxyConfig:
    config_path = Path(path)
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError(f"cannot read configuration {config_path}: {error}") from error

    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ConfigError(f"invalid YAML in {config_path}: {error}") from error

    return parse_config(document)


def parse_config(document: object) -> ProxyConfig:
    root = _mapping(document, "configuration")
    _reject_unknown(root, {"upstream", "server", "defaults", "models", "profiles"}, "configuration")

    if "upstream" not in root:
        raise ConfigError("configuration.upstream is required")
    upstream_data = _mapping(root["upstream"], "configuration.upstream")
    _reject_unknown(
        upstream_data,
        {"url", "connect_timeout", "read_timeout"},
        "configuration.upstream",
    )
    url = _required_string(upstream_data, "url", "configuration.upstream")
    parsed_url = urlsplit(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ConfigError("configuration.upstream.url must be an absolute http or https URL")
    if parsed_url.username is not None or parsed_url.password is not None:
        raise ConfigError("configuration.upstream.url must not contain credentials")
    if parsed_url.query or parsed_url.fragment:
        raise ConfigError("configuration.upstream.url must not contain a query or fragment")

    connect_timeout = _positive_number(
        upstream_data.get("connect_timeout", 10.0),
        "configuration.upstream.connect_timeout",
    )
    read_timeout = _positive_number(
        upstream_data.get("read_timeout", 300.0),
        "configuration.upstream.read_timeout",
    )

    server_data = _mapping(root.get("server", {}), "configuration.server")
    _reject_unknown(
        server_data,
        {"host", "port", "max_policy_body_bytes"},
        "configuration.server",
    )
    host = server_data.get("host", "127.0.0.1")
    if not isinstance(host, str) or not host:
        raise ConfigError("configuration.server.host must be a non-empty string")
    port = server_data.get("port", 11435)
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ConfigError("configuration.server.port must be an integer from 1 to 65535")
    max_body = server_data.get("max_policy_body_bytes", 64 * 1024 * 1024)
    if isinstance(max_body, bool) or not isinstance(max_body, int) or max_body <= 0:
        raise ConfigError("configuration.server.max_policy_body_bytes must be a positive integer")

    defaults = _policy(root.get("defaults", {}), "configuration.defaults")
    models = _policy_collection(root.get("models", {}), "configuration.models")
    profiles = _policy_collection(root.get("profiles", {}), "configuration.profiles")

    return ProxyConfig(
        upstream=UpstreamConfig(
            url=url.rstrip("/"),
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        ),
        server=ServerConfig(host=host, port=port, max_policy_body_bytes=max_body),
        defaults=defaults,
        models=models,
        profiles=profiles,
    )


def _mapping(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{path} must be a mapping")
    for key in value:
        if not isinstance(key, str):
            raise ConfigError(f"{path} keys must be strings")
    return value


def _reject_unknown(value: dict[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ConfigError(f"{path} contains unknown key(s): {', '.join(unknown)}")


def _required_string(value: dict[str, Any], key: str, path: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ConfigError(f"{path}.{key} must be a non-empty string")
    return result


def _positive_number(value: object, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"{path} must be a positive number")
    return float(value)


def _policy(value: object, path: str) -> Policy:
    policy = _mapping(value, path)
    _reject_unknown(policy, {"think", "options"}, path)
    if "think" in policy:
        think = policy["think"]
        if think is not None and not isinstance(think, (bool, str)):
            raise ConfigError(f"{path}.think must be a boolean, string, or null")
    if "options" in policy:
        options = _mapping(policy["options"], f"{path}.options")
        return {**policy, "options": dict(options)}
    return dict(policy)


def _policy_collection(value: object, path: str) -> dict[str, Policy]:
    collection = _mapping(value, path)
    result: dict[str, Policy] = {}
    for name, policy in collection.items():
        if not name:
            raise ConfigError(f"{path} keys must be non-empty strings")
        result[name] = _policy(policy, f'{path}["{name}"]')
    return result
