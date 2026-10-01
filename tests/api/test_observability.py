from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_request_id() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"


def test_health_preserves_supplied_request_id() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"X-Request-ID": "review-test-request"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "review-test-request"
