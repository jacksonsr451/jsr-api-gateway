import json

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.auth_service import AuthServiceClient, get_auth_service_client
from app.services.routes_store import RouteStore, get_route_store


def _auth_client() -> AuthServiceClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "", 1)

        if request.url.path == "/auth/validate":
            if token == "admin-token":
                return httpx.Response(200, json={"sub": "admin", "roles": ["admin"]})
            return httpx.Response(401, json={"detail": "invalid"})

        if request.url.path == "/auth/authorize":
            payload = json.loads(request.content.decode() or "{}")
            if (
                token == "admin-token"
                and payload.get("permission") == "gateway:routes:manage"
            ):
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


def test_routes_crud(tmp_path) -> None:
    store = RouteStore(str(tmp_path / "routes.yaml"))
    app = create_app(Settings.model_validate({"rate_limit_enabled": False}))
    app.dependency_overrides[get_route_store] = lambda: store
    app.dependency_overrides[get_auth_service_client] = _auth_client
    client = TestClient(app)
    headers = {"Authorization": "Bearer admin-token"}

    response = client.post(
        "/api/v1/routes",
        json={
            "name": "users",
            "regex": r"^/users(/.*)?$",
            "upstream_base_url": "http://users.local:8000",
            "methods": ["GET"],
        },
        headers=headers,
    )

    assert response.status_code == 201
    route_id = response.json()["id"]

    list_response = client.get("/api/v1/routes", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.put(
        f"/api/v1/routes/{route_id}",
        json={"name": "users-v2"},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "users-v2"

    delete_response = client.delete(f"/api/v1/routes/{route_id}", headers=headers)
    assert delete_response.status_code == 204
