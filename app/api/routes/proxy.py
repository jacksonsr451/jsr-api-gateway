from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response

from app.schemas.routes import RouteAuth, RouteConfig
from app.services.auth_service import (
    AuthServiceClient,
    AuthServiceError,
    get_auth_service_client,
)
from app.services.proxy_client import ProxyClient, get_proxy_client
from app.services.routes_store import RouteStore, get_route_store

router = APIRouter()

_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


@router.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]
)
async def proxy_request(
    path: str,
    request: Request,
    store: RouteStore = Depends(get_route_store),
    proxy_client: ProxyClient = Depends(get_proxy_client),
    auth_client: AuthServiceClient = Depends(get_auth_service_client),
) -> Response:
    raw_path = f"/{path}" if path else "/"
    route = store.match_route(request.method, raw_path)
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="route_not_found"
        )

    _maybe_authorize(route, request, auth_client)

    upstream_path = _normalize_path(route.rewrite_path(raw_path))
    upstream_url = _build_upstream_url(route.upstream_base_url, upstream_path)
    headers = _build_upstream_headers(request)
    body = await request.body()

    try:
        upstream_response = await proxy_client.request(
            request.method,
            upstream_url,
            headers=headers,
            params=list(request.query_params.multi_items()),
            content=body,
            timeout=route.timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="upstream_timeout"
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="upstream_unavailable"
        ) from exc

    response_headers = _filter_response_headers(upstream_response.headers)
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
    )


def _maybe_authorize(
    route: RouteConfig, request: Request, auth_client: AuthServiceClient
) -> dict:
    auth_config = route.auth or RouteAuth()
    needs_auth = auth_config.required or auth_config.permission or auth_config.roles
    if not needs_auth:
        return {}

    token = _extract_bearer_token(request)
    try:
        claims = auth_client.validate_token(token)
        if auth_config.permission:
            auth_client.authorize(token, auth_config.permission)
        if auth_config.roles:
            _ensure_roles(claims, auth_config.roles)
    except AuthServiceError as exc:
        headers = (
            {"WWW-Authenticate": "Bearer"}
            if exc.status_code == status.HTTP_401_UNAUTHORIZED
            else None
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
            headers=headers,
        ) from exc
    return claims


def _extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def _ensure_roles(claims: dict, required_roles: list[str]) -> None:
    claim_roles = claims.get("roles") if isinstance(claims, dict) else None
    if claim_roles is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not_authorized"
        )
    if isinstance(claim_roles, str):
        roles_set = {claim_roles}
    else:
        roles_set = {str(role) for role in claim_roles}
    if not roles_set.intersection(required_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not_authorized"
        )


def _normalize_path(path: str) -> str:
    if not path:
        return "/"
    if not path.startswith("/"):
        return f"/{path}"
    return path


def _build_upstream_url(base_url: str, path: str) -> str:
    parsed = urlsplit(base_url)
    base_path = parsed.path.rstrip("/")
    full_path = f"{base_path}{path}"
    return urlunsplit((parsed.scheme, parsed.netloc, full_path, "", ""))


def _build_upstream_headers(request: Request) -> dict[str, str]:
    headers = {}
    for key, value in request.headers.items():
        if key.lower() in _HOP_BY_HOP_HEADERS:
            continue
        headers[key] = value

    client_host = request.client.host if request.client else None
    existing_forwarded_for = request.headers.get("X-Forwarded-For")
    if client_host:
        if existing_forwarded_for:
            headers["X-Forwarded-For"] = f"{existing_forwarded_for}, {client_host}"
        else:
            headers["X-Forwarded-For"] = client_host

    headers.setdefault("X-Forwarded-Proto", request.url.scheme)
    if "host" in request.headers:
        headers.setdefault("X-Forwarded-Host", request.headers["host"])
    return headers


def _filter_response_headers(headers: httpx.Headers) -> dict[str, str]:
    filtered: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in _HOP_BY_HOP_HEADERS:
            continue
        filtered[key] = value
    return filtered
