from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore


def test_health_is_public_without_credentials():
    app = create_app(InMemoryAnalysisResultStore(), operator_token="test-token")

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_endpoint_requires_credentials():
    app = create_app(InMemoryAnalysisResultStore(), operator_token="test-token")

    with TestClient(app) as client:
        response = client.get("/api/v1/analysis/EGAL")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_protected_endpoint_rejects_invalid_credentials():
    app = create_app(InMemoryAnalysisResultStore(), operator_token="test-token")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/analysis/EGAL",
            headers={"Authorization": "Bearer wrong-token"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_protected_endpoint_accepts_valid_operator_credentials():
    app = create_app(InMemoryAnalysisResultStore(), operator_token="test-token")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/analysis/EGAL",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Analysis result not found for EGAL"}


def test_unconfigured_authentication_is_explicit(monkeypatch):
    monkeypatch.delenv("EGX_OPERATOR_TOKEN", raising=False)
    app = create_app(InMemoryAnalysisResultStore(), operator_token=None)

    with TestClient(app) as client:
        response = client.get("/api/v1/analysis/EGAL")

    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication is not configured"}


def test_operator_token_is_not_returned_in_error_response():
    app = create_app(InMemoryAnalysisResultStore(), operator_token="test-token")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/analysis/EGAL",
            headers={"Authorization": "Bearer wrong-token"},
        )

    assert "wrong-token" not in response.text
    assert "test-token" not in response.text
