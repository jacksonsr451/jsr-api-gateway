from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _client() -> TestClient:
    settings = Settings.model_validate({"rate_limit_enabled": False})
    return TestClient(create_app(settings))


def test_openapi_includes_routes() -> None:
    client = _client()

    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    paths = payload["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/routes" in paths
    assert "/api/v1/routes/{route_id}" in paths
    assert "/api/v1/{path}" not in paths


def test_openapi_documents_error_responses() -> None:
    client = _client()

    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    responses = payload["paths"]["/api/v1/routes"]["get"]["responses"]
    assert "401" in responses
    schema = responses["401"]["content"]["application/json"]["schema"]
    assert schema["$ref"].endswith("/ErrorResponse")
    tags = {tag["name"] for tag in payload.get("tags", [])}
    assert "health" in tags
    assert "gateway" in tags
