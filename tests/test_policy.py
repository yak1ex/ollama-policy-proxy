from __future__ import annotations

import pytest

from ollama_policy_proxy.config import parse_config
from ollama_policy_proxy.policy import UnknownProfileError, apply_policy


@pytest.fixture
def config():
    return parse_config(
        {
            "upstream": {"url": "http://upstream"},
            "defaults": {
                "think": False,
                "options": {"num_predict": 2048, "temperature": 0.7, "seed": 1},
            },
            "models": {
                "reasoning": {
                    "think": True,
                    "options": {"num_predict": 8192, "seed": 2},
                }
            },
            "profiles": {
                "fast": {"think": False, "options": {"num_predict": 1024, "seed": 3}},
                "deep": {"think": "high", "options": {"num_predict": 16384}},
            },
        }
    )


def test_global_defaults_apply_when_fields_are_absent(config) -> None:
    original = {"model": "plain", "prompt": "hello", "stream": False}

    result = apply_policy(original, config)

    assert result["think"] is False
    assert result["options"] == {"num_predict": 2048, "temperature": 0.7, "seed": 1}
    assert result["prompt"] == "hello"
    assert original == {"model": "plain", "prompt": "hello", "stream": False}


def test_model_and_profile_override_by_individual_option_key(config) -> None:
    result = apply_policy({"model": "reasoning", "prompt": "hello"}, config, "fast")

    assert result["think"] is False
    assert result["options"] == {"num_predict": 1024, "temperature": 0.7, "seed": 3}


def test_explicit_request_values_have_highest_precedence(config) -> None:
    result = apply_policy(
        {
            "model": "reasoning",
            "prompt": "hello",
            "think": False,
            "options": {"num_predict": 0, "temperature": None},
        },
        config,
        "deep",
    )

    assert result["think"] is False
    assert result["options"] == {"num_predict": 0, "temperature": None, "seed": 2}


def test_explicit_null_options_are_preserved(config) -> None:
    result = apply_policy({"model": "reasoning", "options": None}, config, "fast")

    assert result["options"] is None


def test_unknown_profile(config) -> None:
    with pytest.raises(UnknownProfileError, match="missing"):
        apply_policy({"model": "plain"}, config, "missing")
