from __future__ import annotations

import math
import time
from dataclasses import dataclass
from threading import Lock
from typing import Callable, Iterable

from fastapi import Request, status
from fastapi.responses import ORJSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.responses import build_error_payload


@dataclass
class RateLimitState:
    window_start: float
    count: int


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_seconds: int


class RateLimiter:
    def __init__(
        self,
        *,
        limit: int,
        window_seconds: int,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._clock = clock or time.monotonic
        self._state: dict[str, RateLimitState] = {}
        self._lock = Lock()

    def hit(self, key: str) -> RateLimitResult:
        now = self._clock()
        with self._lock:
            state = self._state.get(key)
            if state is None or now - state.window_start >= self._window_seconds:
                state = RateLimitState(window_start=now, count=0)
            state.count += 1
            self._state[key] = state

            remaining = max(self._limit - state.count, 0)
            reset_seconds = max(
                0, int(math.ceil(self._window_seconds - (now - state.window_start)))
            )
            allowed = state.count <= self._limit
        return RateLimitResult(
            allowed=allowed,
            limit=self._limit,
            remaining=remaining,
            reset_seconds=reset_seconds,
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        limiter: RateLimiter,
        enabled: bool = True,
        exempt_paths: Iterable[str] | None = None,
        key_header: str = "X-Forwarded-For",
    ) -> None:
        super().__init__(app)
        self._limiter = limiter
        self._enabled = enabled
        self._key_header = key_header
        self._exempt_paths = _normalize_exempt_paths(exempt_paths or [])

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not self._enabled or request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if _is_exempt(path, self._exempt_paths):
            return await call_next(request)

        key = _get_client_key(request, self._key_header)
        result = self._limiter.hit(key)

        if not result.allowed:
            return ORJSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=build_error_payload("rate_limited", "rate_limited"),
                headers=_rate_limit_headers(result, blocked=True),
            )

        response = await call_next(request)
        response.headers.update(_rate_limit_headers(result, blocked=False))
        return response


def _rate_limit_headers(result: RateLimitResult, *, blocked: bool) -> dict[str, str]:
    headers = {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(result.reset_seconds),
    }
    if blocked:
        headers["Retry-After"] = str(result.reset_seconds)
    return headers


def _get_client_key(request: Request, key_header: str) -> str:
    forwarded = request.headers.get(key_header)
    if forwarded:
        candidate = forwarded.split(",")[0].strip()
        if candidate:
            return candidate
    if request.client:
        return request.client.host
    return "unknown"


def _normalize_exempt_paths(paths: Iterable[str]) -> list[str]:
    normalized = []
    for path in paths:
        trimmed = path.strip()
        if not trimmed:
            continue
        cleaned = trimmed.rstrip("/") or "/"
        normalized.append(cleaned)
    return normalized


def _is_exempt(path: str, exempt_paths: Iterable[str]) -> bool:
    for exempt in exempt_paths:
        if exempt == "/":
            return True
        if path == exempt or path.startswith(f"{exempt}/"):
            return True
    return False
