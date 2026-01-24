from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any, cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.core.responses import build_error_payload

logger = logging.getLogger(__name__)

_CODE_NORMALIZE = re.compile(r"[^a-z0-9]+")

_DEFAULT_CODES = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "not_authenticated",
    status.HTTP_403_FORBIDDEN: "not_authorized",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "validation_error",
    status.HTTP_429_TOO_MANY_REQUESTS: "rate_limited",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "internal_server_error",
    status.HTTP_502_BAD_GATEWAY: "bad_gateway",
    status.HTTP_503_SERVICE_UNAVAILABLE: "service_unavailable",
    status.HTTP_504_GATEWAY_TIMEOUT: "gateway_timeout",
}


ExceptionHandler = Callable[[Request, Exception], Response | Awaitable[Response]]


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        StarletteHTTPException,
        cast(ExceptionHandler, http_exception_handler),
    )
    app.add_exception_handler(
        RequestValidationError,
        cast(ExceptionHandler, validation_exception_handler),
    )
    app.add_exception_handler(
        Exception,
        cast(ExceptionHandler, unhandled_exception_handler),
    )


def _normalize_code(value: str) -> str:
    cleaned = _CODE_NORMALIZE.sub("_", value.strip().lower()).strip("_")
    return cleaned or "error"


def _default_code(status_code: int) -> str:
    return _DEFAULT_CODES.get(status_code, "http_error")


def _extract_error(detail: Any, *, default_code: str) -> tuple[str, str, Any | None]:
    if isinstance(detail, str):
        return _normalize_code(detail), detail, None

    if isinstance(detail, dict):
        if "code" in detail:
            raw_code = str(detail["code"])
            message = str(detail.get("message", raw_code))
            details = detail.get("details")
            extra = {
                key: value
                for key, value in detail.items()
                if key not in {"code", "message", "details"}
            }
            if extra:
                details = details or extra
            return _normalize_code(raw_code), message, details

        if "detail" in detail and isinstance(detail["detail"], str):
            raw = detail["detail"]
            extras = {key: value for key, value in detail.items() if key != "detail"}
            return _normalize_code(raw), raw, extras or None

    details = detail if detail not in (None, "") else None
    return default_code, default_code, details


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> ORJSONResponse:
    code, message, details = _extract_error(
        exc.detail, default_code=_default_code(exc.status_code)
    )
    return ORJSONResponse(
        status_code=exc.status_code,
        content=build_error_payload(code, message, details),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_error_payload(
            code="validation_error",
            message="validation_error",
            details=exc.errors(),
        ),
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> ORJSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=build_error_payload(
            code="internal_server_error",
            message="internal_server_error",
        ),
    )
