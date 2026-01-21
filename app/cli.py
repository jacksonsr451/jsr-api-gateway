from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi_cli.cli import main as fastapi_main

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def _load_env() -> None:
    if _ENV_PATH.exists():
        load_dotenv(_ENV_PATH, override=False)


def _inject_host_port(args: list[str]) -> list[str]:
    if not args:
        return args
    if args[0] not in {"run", "dev"}:
        return args

    if "--host" not in args and os.getenv("APP_HOST"):
        args = args + ["--host", os.environ["APP_HOST"]]
    if "--port" not in args and os.getenv("APP_PORT"):
        args = args + ["--port", os.environ["APP_PORT"]]
    return args


def main() -> None:
    _load_env()
    if "PORT" not in os.environ and os.getenv("APP_PORT"):
        os.environ["PORT"] = os.environ["APP_PORT"]
    sys.argv = [sys.argv[0]] + _inject_host_port(sys.argv[1:])
    fastapi_main()
