from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.authentication import ApiAuthentication
from app.application.security.authentication import AuthenticationError
from app.application.security.identity import AuthenticatedIdentity


class StubAuthenticator:
    def __init__(
        self,
        identity: AuthenticatedIdentity | None = None,
        error: Exception | None = None,
    ) -> None:
        self.identity = identity
        self.error = error

    def authenticate(self, authorization_header: str | None) -> AuthenticatedIdentity:
        if self.error is not None:
            raise self.error
        assert self.identity is not None
        return self.identity


def make_app(authenticator: StubAuthenticator) -> FastAPI:
    app = FastAPI()
    api_authentication = ApiAuthentication(
        operator_token=None,
        authenticator=authenticator,
        legacy_test_composition=False,
    )

    @app.get("/me")
    def me(
        identity: AuthenticatedIdentity = Depends(api_authentication.require_authenticated),
    ) -> dict[str, str]:
        return {"subject": identity.subject}

    @app.get("/operator")
    def operator(
        identity: AuthenticatedIdentity = Depends(api_authentication.require_operator),
    ) -> dict[str, str]:
        return {"subject": identity.subject}

    return app


def test_authentication_adapter_maps_authentication_error_to_401() -> None:
    app = make_app(StubAuthenticator(error=AuthenticationError("invalid")))

    response = TestClient(app).get("/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_authentication_adapter_preserves_authenticated_identity() -> None:
    identity = AuthenticatedIdentity.user(uuid4())

    response = TestClient(make_app(StubAuthenticator(identity=identity))).get(
        "/me",
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 200
    assert response.json() == {"subject": identity.subject}


def test_operator_dependency_rejects_non_operator_identity() -> None:
    identity = AuthenticatedIdentity.user(uuid4())

    response = TestClient(make_app(StubAuthenticator(identity=identity))).get(
        "/operator",
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 403


def test_operator_dependency_accepts_operator_identity() -> None:
    response = TestClient(
        make_app(StubAuthenticator(identity=AuthenticatedIdentity.operator()))
    ).get("/operator", headers={"Authorization": "Bearer test"})

    assert response.status_code == 200
    assert response.json() == {"subject": "operator"}
