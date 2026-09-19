from typing import Protocol

from app.application.security.identity import AuthenticatedIdentity


class AuthenticationError(ValueError):
    """Raised when authentication cannot establish an identity."""


class Authenticator(Protocol):
    def authenticate(self, authorization_header: str | None) -> AuthenticatedIdentity:
        ...
