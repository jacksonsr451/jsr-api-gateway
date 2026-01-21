from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _client(*, limit: int = 2, window_seconds: int = 60) -> TestClient:
    settings = Settings(
        rate_limit_enabled=True,
        rate_limit_requests=limit,
        rate_limit_window_seconds=window_seconds,
    )
    app = create_app(settings)
    return TestClient(app)


def test_rate_limit_blocks_after_limit() -> None:
    client = _client(limit=2)
    headers = {"X-Forwarded-For": "203.0.113.10"}

    assert client.get("/api/v1/health", headers=headers).status_code == 200
    assert client.get("/api/v1/health", headers=headers).status_code == 200

    response = client.get("/api/v1/health", headers=headers)

    assert response.status_code == 429
    assert response.headers["retry-after"].isdigit()
    assert response.json() == {"detail": "rate_limited"}


def test_rate_limit_is_per_client() -> None:
    client = _client(limit=1)

    response_a = client.get("/api/v1/health", headers={"X-Forwarded-For": "10.0.0.1"})
    response_b = client.get("/api/v1/health", headers={"X-Forwarded-For": "10.0.0.2"})

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    blocked_a = client.get("/api/v1/health", headers={"X-Forwarded-For": "10.0.0.1"})
    blocked_b = client.get("/api/v1/health", headers={"X-Forwarded-For": "10.0.0.2"})

    assert blocked_a.status_code == 429
    assert blocked_b.status_code == 429
