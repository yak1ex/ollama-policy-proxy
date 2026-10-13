from __future__ import annotations

import pytest

from ollama_policy_proxy.config import ConfigError, load_config, parse_config


def test_config_defaults_and_thinking_types() -> None:
    config = parse_config(
        {
            "upstream": {"url": "http://127.0.0.1:11434/"},
            "defaults": {"think": None, "options": {"num_predict": 2048}},
            "models": {"gpt-oss": {"think": "low"}},
            "profiles": {"fast": {"think": False}},
        }
    )

    assert config.upstream.url == "http://127.0.0.1:11434"
    assert config.server.host == "127.0.0.1"
    assert config.server.port == 11435
    assert config.defaults["think"] is None
    assert config.models["gpt-oss"]["think"] == "low"


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ({}, "configuration.upstream is required"),
        ({"upstream": {"url": "file:///tmp/ollama"}}, "absolute http or https URL"),
        ({"upstream": {"url": "http://user:password@host"}}, "must not contain credentials"),
        ({"upstream": {"url": "http://host/?next=elsewhere"}}, "query or fragment"),
        ({"upstream": {"url": "http://host"}, "server": {"port": 0}}, "1 to 65535"),
        (
            {"upstream": {"url": "http://host"}, "defaults": {"think": 1}},
            "boolean, string, or null",
        ),
        (
            {"upstream": {"url": "http://host"}, "profiles": {"fast": {"extra": True}}},
            r"unknown key\(s\): extra",
        ),
    ],
)
def test_invalid_configuration_is_actionable(document: object, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        parse_config(document)


def test_invalid_yaml_reports_file_context(tmp_path) -> None:
    config_path = tmp_path / "broken.yml"
    config_path.write_text("upstream: [", encoding="utf-8")

    with pytest.raises(ConfigError, match=r"invalid YAML in .*broken\.yml"):
        load_config(config_path)
