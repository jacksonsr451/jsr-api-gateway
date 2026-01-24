import json
from typing import Any

import httpx
from fastapi import Depends, FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.testclient import TestClient

from app.api.deps import require_authentication, require_authorization
from app.core.exception_handlers import register_exception_handlers
from app.core.responses import build_data_payload
from app.services.auth_service import (
    AuthContext,
    AuthServiceClient,
    get_auth_service_client,
)


def _build_app(client: AuthServiceClient) -> FastAPI:
    app = FastAPI(default_response_class=ORJSONResponse)
    register_exception_handlers(app)
    app.dependency_overrides[get_auth_service_client] = lambda: client

    @app.get("/protected")
    async def protected(
        context: AuthContext = Depends(require_authentication),
    ) -> dict[str, Any]:
        return build_data_payload({"subject": context.claims.get("sub")})

    @app.get("/admin")
    async def admin(
        context: AuthContext = Depends(require_authorization("admin:read")),
    ) -> dict[str, Any]:
        return build_data_payload({"ok": True})

    return app


def _json_payload(request: httpx.Request) -> dict[str, Any]:
    if not request.content:
        return {}
    return json.loads(request.content.decode())


def _mock_transport() -> httpx.MockTransport:
    async def handler(request: httpx.Request) -> httpx.Response:
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "", 1)

        if request.url.path == "/auth/validate":
            if token in {"valid-token", "limited-token"}:
                return httpx.Response(200, json={"sub": "user-123"})
            if token == "admin-token":
                return httpx.Response(200, json={"sub": "admin-1"})
            return httpx.Response(401, json={"detail": "invalid"})

        if request.url.path == "/auth/authorize":
            payload = _json_payload(request)
            permission = payload.get("permission")
            if token == "admin-token" and permission == "admin:read":
                return httpx.Response(204)
            if token == "limited-token" and permission == "admin:read":
                return httpx.Response(403, json={"detail": "forbidden"})
            return httpx.Response(401, json={"detail": "invalid"})

        return httpx.Response(404, json={"detail": "not_found"})

    return httpx.MockTransport(handler)


def _auth_client(transport: httpx.AsyncBaseTransport) -> AuthServiceClient:
    return AuthServiceClient(
        base_url="http://auth-service.local",
        timeout=1.0,
        validate_path="/auth/validate",
        authorize_path="/auth/authorize",
        transport=transport,
    )


def test_auth_missing_token_returns_401() -> None:
    app = _build_app(_auth_client(_mock_transport()))
    client = TestClient(app)

    response = client.get("/protected")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "error": {"code": "not_authenticated", "message": "not_authenticated"}
    }


def test_auth_invalid_token_returns_401() -> None:
    app = _build_app(_auth_client(_mock_transport()))
    client = TestClient(app)

    response = client.get("/protected", headers={"Authorization": "Bearer bad-token"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_auth_valid_token_allows_request() -> None:
    app = _build_app(_auth_client(_mock_transport()))
    client = TestClient(app)

    response = client.get("/protected", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == 200
    assert response.json() == {"data": {"subject": "user-123"}}


def test_authorization_forbidden_returns_403() -> None:
    app = _build_app(_auth_client(_mock_transport()))
    client = TestClient(app)

    response = client.get("/admin", headers={"Authorization": "Bearer limited-token"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_authorized"


def test_authorization_allows_admin() -> None:
    app = _build_app(_auth_client(_mock_transport()))
    client = TestClient(app)

    response = client.get("/admin", headers={"Authorization": "Bearer admin-token"})

    assert response.status_code == 200
    assert response.json() == {"data": {"ok": True}}


def test_auth_service_unavailable_returns_503() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    app = _build_app(_auth_client(httpx.MockTransport(handler)))
    client = TestClient(app)

    response = client.get("/protected", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "auth_service_unavailable"
