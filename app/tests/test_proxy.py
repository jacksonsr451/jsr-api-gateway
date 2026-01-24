import json

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.schemas.routes import RouteAuth, RouteCreate, RouteRewrite
from app.services.auth_service import AuthServiceClient, get_auth_service_client
from app.services.proxy_client import ProxyClient, get_proxy_client
from app.services.routes_store import RouteStore, get_route_store


def _auth_client() -> AuthServiceClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "", 1)

        if request.url.path == "/auth/validate":
            if token == "admin-token":
                return httpx.Response(200, json={"roles": ["admin"], "sub": "admin-1"})
            if token == "user-token":
                return httpx.Response(200, json={"roles": ["user"], "sub": "user-1"})
            return httpx.Response(401, json={"detail": "invalid"})

        if request.url.path == "/auth/authorize":
            payload = json.loads(request.content.decode() or "{}")
            permission = payload.get("permission")
            if token == "admin-token" and permission == "users:read":
                return httpx.Response(204)
            return httpx.Response(403, json={"detail": "forbidden"})

        return httpx.Response(404, json={"detail": "not_found"})

    return AuthServiceClient(
        base_url="http://auth.local",
        timeout=1.0,
        validate_path="/auth/validate",
        authorize_path="/auth/authorize",
        transport=httpx.MockTransport(handler),
    )


def _proxy_client(record: dict) -> ProxyClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        record["path"] = request.url.path
        record["query"] = request.url.query
        return httpx.Response(200, json={"proxied": True})

    return ProxyClient(timeout=1.0, transport=httpx.MockTransport(handler))


def _setup_app(tmp_path):
    store = RouteStore(str(tmp_path / "routes.yaml"))
    store.create_route(
        RouteCreate(
            name="users",
            regex=r"^/users/(\d+)$",
            upstream_base_url="http://upstream.local",
            methods=["GET"],
            rewrite=RouteRewrite(regex_uri=(r"^/users/(\d+)$", r"/members/\1")),
            auth=RouteAuth(required=True, permission="users:read", roles=["admin"]),
            priority=10,
        )
    )

    app = create_app(Settings.model_validate({"rate_limit_enabled": False}))
    app.dependency_overrides[get_route_store] = lambda: store
    app.dependency_overrides[get_auth_service_client] = _auth_client
    return app


def test_proxy_rewrite_and_forward(tmp_path) -> None:
    record: dict[str, str] = {}
    app = _setup_app(tmp_path)
    app.dependency_overrides[get_proxy_client] = lambda: _proxy_client(record)
    client = TestClient(app)

    response = client.get(
        "/api/v1/users/42?expand=1", headers={"Authorization": "Bearer admin-token"}
    )

    assert response.status_code == 200
    assert response.json() == {"proxied": True}
    assert record["path"] == "/members/42"
    assert record["query"] == b"expand=1"


def test_proxy_blocks_invalid_role(tmp_path) -> None:
    record: dict[str, str] = {}
    app = _setup_app(tmp_path)
    app.dependency_overrides[get_proxy_client] = lambda: _proxy_client(record)
    client = TestClient(app)

    response = client.get(
        "/api/v1/users/42", headers={"Authorization": "Bearer user-token"}
    )

    assert response.status_code == 403
    assert record == {}


def test_proxy_returns_404_when_no_route(tmp_path) -> None:
    app = _setup_app(tmp_path)
    app.dependency_overrides[get_proxy_client] = lambda: _proxy_client({})
    client = TestClient(app)

    response = client.get(
        "/api/v1/unknown", headers={"Authorization": "Bearer admin-token"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "route_not_found"
