from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import status

from app.core.config import get_settings


@dataclass(frozen=True)
class AuthContext:
    token: str
    claims: dict[str, Any]


class AuthServiceError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class AuthServiceClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout: float,
        validate_path: str,
        authorize_path: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._validate_path = _normalize_path(validate_path)
        self._authorize_path = _normalize_path(authorize_path)
        self._transport = transport

    def validate_token(self, token: str) -> dict[str, Any]:
        response = self._request("POST", self._validate_path, token, payload=None)
        if response.status_code == status.HTTP_200_OK:
            return self._parse_claims(response)
        if response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ):
            raise AuthServiceError(response.status_code, "invalid_token")
        raise AuthServiceError(status.HTTP_502_BAD_GATEWAY, "auth_service_error")

    def authorize(self, token: str, permission: str) -> None:
        response = self._request(
            "POST",
            self._authorize_path,
            token,
            payload={"permission": permission},
        )
        if response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
        ):
            return
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            raise AuthServiceError(status.HTTP_401_UNAUTHORIZED, "invalid_token")
        if response.status_code == status.HTTP_403_FORBIDDEN:
            raise AuthServiceError(status.HTTP_403_FORBIDDEN, "not_authorized")
        raise AuthServiceError(status.HTTP_502_BAD_GATEWAY, "auth_service_error")

    def _request(
        self,
        method: str,
        path: str,
        token: str,
        payload: dict[str, Any] | None,
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            with httpx.Client(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                return client.request(method, path, headers=headers, json=payload)
        except httpx.RequestError as exc:
            raise AuthServiceError(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "auth_service_unavailable",
            ) from exc

    def _parse_claims(self, response: httpx.Response) -> dict[str, Any]:
        if not response.content:
            return {}
        try:
            data = response.json()
        except ValueError as exc:
            raise AuthServiceError(
                status.HTTP_502_BAD_GATEWAY,
                "auth_service_invalid_response",
            ) from exc
        if isinstance(data, dict):
            return data
        return {"data": data}


def get_auth_service_client() -> AuthServiceClient:
    settings = get_settings()
    return AuthServiceClient(
        base_url=settings.auth_service_base_url,
        timeout=settings.auth_service_timeout_seconds,
        validate_path=settings.auth_service_validate_path,
        authorize_path=settings.auth_service_authorize_path,
    )


def _normalize_path(path: str) -> str:
    if not path.startswith("/"):
        return f"/{path}"
    return path
