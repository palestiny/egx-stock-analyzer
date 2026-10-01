from __future__ import annotations

import os

from fastapi import Header, HTTPException

from app.application.security.authentication import (
    AuthenticationError,
    Authenticator,
    BearerTokenAuthenticator,
)
from app.application.security.authorization import AuthorizationError, OperatorAuthorizer
from app.application.security.identity import AuthenticatedIdentity, Permission


class ApiAuthentication:
    """HTTP adapter for authentication and operator authorization.

    The application/domain layers remain unaware of FastAPI headers and HTTP
    status codes. Keeping this adapter separate also makes the API composition
    root easier to reason about and test.
    """

    def __init__(
        self,
        *,
        operator_token: str | None,
        authenticator: Authenticator | None,
        legacy_test_composition: bool,
    ) -> None:
        self._authenticator = authenticator
        self._operator_authenticator = (
            BearerTokenAuthenticator(operator_token) if operator_token else None
        )
        self._legacy_test_composition = legacy_test_composition
        self._authorizer = OperatorAuthorizer()

    def require_authenticated(
        self,
        authorization: str | None = Header(default=None),
    ) -> AuthenticatedIdentity:
        if self._legacy_test_composition:
            return AuthenticatedIdentity.operator()

        if self._authenticator is None:
            if self._operator_authenticator is None:
                raise HTTPException(status_code=503, detail="Authentication is not configured")
            authenticator = self._operator_authenticator
        else:
            authenticator = self._authenticator

        try:
            return authenticator.authenticate(authorization)
        except AuthenticationError as error:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            ) from error

    def require_operator(
        self,
        authorization: str | None = Header(default=None),
    ) -> AuthenticatedIdentity:
        if self._legacy_test_composition:
            return AuthenticatedIdentity.operator()

        try:
            identity = self.require_authenticated(authorization)
            self._authorizer.require(identity, Permission.OPERATOR)
            return identity
        except AuthorizationError as error:
            raise HTTPException(status_code=403, detail="Forbidden") from error
