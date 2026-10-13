from __future__ import annotations

from copy import deepcopy
from typing import Any

from .config import Policy, ProxyConfig


class UnknownProfileError(ValueError):
    """Raised when a request selects a profile that is not configured."""


def apply_policy(
    request_body: dict[str, Any],
    config: ProxyConfig,
    profile_name: str | None = None,
) -> dict[str, Any]:
    """Return a request body with missing policy-controlled values filled in."""
    layers: list[Policy] = [config.defaults]
    model = request_body.get("model")
    if isinstance(model, str) and model in config.models:
        layers.append(config.models[model])
    if profile_name is not None:
        try:
            layers.append(config.profiles[profile_name])
        except KeyError as error:
            raise UnknownProfileError(profile_name) from error

    effective: Policy = {}
    effective_options: dict[str, Any] = {}
    for layer in layers:
        if "think" in layer:
            effective["think"] = deepcopy(layer["think"])
        if "options" in layer:
            effective_options.update(deepcopy(layer["options"]))

    result = deepcopy(request_body)
    if "think" not in result and "think" in effective:
        result["think"] = effective["think"]

    if "options" not in result:
        if effective_options:
            result["options"] = effective_options
    elif isinstance(result["options"], dict):
        merged_options = effective_options
        merged_options.update(result["options"])
        result["options"] = merged_options

    return result
