from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence

from aiohttp import web

from .config import ConfigError, load_config
from .proxy import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ollama-policy-proxy",
        description="Apply configurable defaults while proxying the Ollama API.",
    )
    parser.add_argument("--config", required=True, help="path to the YAML configuration file")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="operational log level (request bodies are never logged)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        config = load_config(args.config)
    except ConfigError as error:
        raise SystemExit(f"configuration error: {error}") from error

    logging.getLogger("ollama_policy_proxy").info(
        "starting proxy on %s:%s with upstream %s",
        config.server.host,
        config.server.port,
        config.upstream.url,
    )
    web.run_app(
        create_app(config),
        host=config.server.host,
        port=config.server.port,
        print=None,
    )
