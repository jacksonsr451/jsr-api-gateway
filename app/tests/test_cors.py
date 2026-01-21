from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def _allowed_origin() -> str:
    settings = get_settings()
    if "*" in settings.cors_allow_origins or not settings.cors_allow_origins:
        return "http://example.com"
    return settings.cors_allow_origins[0]


def _expected_allow_origin(origin: str) -> str:
    settings = get_settings()
    if "*" in settings.cors_allow_origins and not settings.cors_allow_credentials:
        return "*"
    return origin


def test_cors_preflight_allows_origin() -> None:
    client = TestClient(app)
    origin = _allowed_origin()

    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == _expected_allow_origin(
        origin
    )
    assert "GET" in response.headers["access-control-allow-methods"]


def test_cors_simple_request_adds_allow_origin() -> None:
    client = TestClient(app)
    origin = _allowed_origin()

    response = client.get("/api/v1/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == _expected_allow_origin(
        origin
    )
