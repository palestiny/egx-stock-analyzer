from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.security.authorization import AuthorizationError, require_permission
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.infrastructure.security.bearer_token_authenticator import (
    AuthenticationError,
    BearerTokenAuthenticator,
)


def test_missing_bearer_credentials_are_rejected():
    app = create_app(InMemoryAnalysisResultStore(), operator_token="secret")

    with TestClient(app) as client:
        response = client.get("/api/v1/analysis/EGAL")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_invalid_bearer_credentials_are_rejected_without_disclosing_validation_details():
    app = create_app(InMemoryAnalysisResultStore(), operator_token="secret")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/analysis/EGAL",
            headers={"Authorization": "Bearer wrong"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
    assert "secret" not in response.text


def test_valid_operator_credentials_reach_protected_endpoint():
    app = create_app(InMemoryAnalysisResultStore(), operator_token="secret")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/analysis/EGAL",
            headers={"Authorization": "Bearer secret"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Analysis result not found for EGAL"}


def test_health_remains_public():
    app = create_app(InMemoryAnalysisResultStore(), operator_token="secret")

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_bearer_authenticator_returns_operator_identity():
    identity = BearerTokenAuthenticator("secret").authenticate("Bearer secret")

    assert identity.subject == "operator"
    assert Permission.OPERATOR in identity.permissions


def test_bearer_authenticator_rejects_malformed_or_invalid_credentials():
    authenticator = BearerTokenAuthenticator("secret")

    for header in (None, "", "Basic secret", "Bearer", "Bearer wrong"):
        try:
            authenticator.authenticate(header)
        except AuthenticationError as error:
            assert str(error) == "Invalid authentication credentials"
        else:
            raise AssertionError("Expected authentication failure")


def test_bearer_authenticator_rejects_empty_configuration():
    try:
        BearerTokenAuthenticator("  ")
    except ValueError as error:
        assert str(error) == "Operator token must be configured"
    else:
        raise AssertionError("Expected configuration validation failure")


def test_authorization_rejects_identity_without_required_permission():
    identity = AuthenticatedIdentity(
        subject="future-user",
        permissions=frozenset(),
    )

    try:
        require_permission(identity, Permission.OPERATOR)
    except AuthorizationError as error:
        assert str(error) == "Required permission is not available"
    else:
        raise AssertionError("Expected authorization failure")
