from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.security.authentication import ConfiguredBearerTokenAuthenticator
from app.application.security.identity import LEGACY_OPERATOR_USER_ID
from app.domain.identity.user import User, UserStatus


class InMemoryUserStore:
    def __init__(self, users):
        self._users = {user.id: user for user in users}

    def get(self, user_id):
        return self._users.get(user_id)


def configured_test_authenticator():
    store = InMemoryUserStore([User(LEGACY_OPERATOR_USER_ID, UserStatus.ACTIVE)])
    return ConfiguredBearerTokenAuthenticator(
        {},
        user_store=store,
        legacy_operator_token="test-token",
    )


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


def test_authenticated_identity_endpoint_returns_identity_without_credentials():
    app = create_app(
        InMemoryAnalysisResultStore(),
        authenticator=configured_test_authenticator(),
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200
    assert response.json()["subject"] == "operator"
    assert response.json()["status"] == "active"
    assert response.json()["user_id"] == "00000000-0000-0000-0000-000000000001"


def test_authenticated_identity_endpoint_rejects_missing_credentials():
    app = create_app(
        InMemoryAnalysisResultStore(),
        authenticator=configured_test_authenticator(),
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401



def test_repeated_invalid_credentials_are_rate_limited():
    app = create_app(InMemoryAnalysisResultStore(), operator_token="test-token")

    with TestClient(app) as client:
        for _ in range(10):
            response = client.get(
                "/api/v1/analysis/EGAL",
                headers={"Authorization": "Bearer wrong-token"},
            )
            assert response.status_code == 401

        blocked = client.get(
            "/api/v1/analysis/EGAL",
            headers={"Authorization": "Bearer wrong-token"},
        )

    assert blocked.status_code == 429
    assert blocked.headers["retry-after"]



def test_cors_allows_only_configured_origin(monkeypatch):
    monkeypatch.setenv("EGX_CORS_ALLOWED_ORIGINS", "https://dashboard.example.com")
    app = create_app(InMemoryAnalysisResultStore(), operator_token="test-token")

    with TestClient(app) as client:
        allowed = client.options(
            "/api/v1/auth/me",
            headers={
                "Origin": "https://dashboard.example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        denied = client.options(
            "/api/v1/auth/me",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed.headers["access-control-allow-origin"] == "https://dashboard.example.com"
    assert "access-control-allow-origin" not in denied.headers


def test_cors_rejects_wildcard_with_credentials(monkeypatch):
    import pytest

    monkeypatch.setenv("EGX_CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(ValueError, match="explicit origins"):
        create_app(InMemoryAnalysisResultStore(), operator_token="test-token")
