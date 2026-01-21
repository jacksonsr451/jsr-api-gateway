from __future__ import annotations

from typing import Mapping, Sequence, TypeAlias

import httpx

from app.core.config import get_settings

QueryParamValue: TypeAlias = str | int | float | bool | None
QueryParamsType: TypeAlias = (
    httpx.QueryParams
    | Mapping[str, QueryParamValue | Sequence[QueryParamValue]]
    | list[tuple[str, QueryParamValue]]
    | tuple[tuple[str, QueryParamValue], ...]
    | str
    | bytes
)


class ProxyClient:
    def __init__(
        self,
        *,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timeout = timeout
        self._transport = transport

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        params: QueryParamsType | None,
        content: bytes | None,
        timeout: float | None = None,
    ) -> httpx.Response:
        request_timeout = timeout or self._timeout
        async with httpx.AsyncClient(
            timeout=request_timeout, transport=self._transport
        ) as client:
            return await client.request(
                method,
                url,
                headers=headers,
                params=params,
                content=content,
            )


def get_proxy_client() -> ProxyClient:
    settings = get_settings()
    return ProxyClient(timeout=settings.proxy_timeout_seconds)
