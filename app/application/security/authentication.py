from collections.abc import Mapping
from secrets import compare_digest
from uuid import UUID

from app.application.identity.user_store import UserStore
from app.application.security.identity import (
    AuthenticatedIdentity,
    LEGACY_OPERATOR_USER_ID,
)
from app.domain.identity.user import UserStatus


class AuthenticationError(ValueError):
    """Raised when supplied authentication credentials are missing or invalid."""


class BearerTokenAuthenticator:
    def __init__(self, expected_token: str) -> None:
        normalized = expected_token.strip()
        if not normalized:
            raise ValueError("operator token cannot be empty")
        self._expected_token = normalized

    def authenticate(self, authorization_header: str | None) -> AuthenticatedIdentity:
        if not authorization_header:
            raise AuthenticationError("Authentication credentials are required")

        scheme, separator, token = authorization_header.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            raise AuthenticationError("Authentication credentials are invalid")

        if not compare_digest(token.strip(), self._expected_token):
            raise AuthenticationError("Authentication credentials are invalid")

        return AuthenticatedIdentity.operator()


class ConfiguredBearerTokenAuthenticator:
    """Resolve configured bearer credentials to active application users."""

    def __init__(
        self,
        user_tokens: Mapping[str, UUID],
        *,
        user_store: UserStore,
        legacy_operator_token: str | None = None,
    ) -> None:
        self._user_tokens = tuple(
            (token.strip(), user_id)
            for token, user_id in user_tokens.items()
            if token.strip()
        )
        if any(user_id == LEGACY_OPERATOR_USER_ID for _, user_id in self._user_tokens):
            raise ValueError("legacy operator identity cannot be configured as a user credential")

        self._user_store = user_store
        self._legacy_operator_token = (
            legacy_operator_token.strip() if legacy_operator_token else None
        )

    def authenticate(self, authorization_header: str | None) -> AuthenticatedIdentity:
        token = self._extract_token(authorization_header)

        if self._legacy_operator_token is not None and compare_digest(
            token, self._legacy_operator_token
        ):
            user = self._user_store.get(LEGACY_OPERATOR_USER_ID)
            if user is None or user.status is not UserStatus.ACTIVE:
                raise AuthenticationError("Authentication credentials are invalid")
            return AuthenticatedIdentity.operator()

        for configured_token, user_id in self._user_tokens:
            if not compare_digest(token, configured_token):
                continue

            user = self._user_store.get(user_id)
            if user is None or user.status is not UserStatus.ACTIVE:
                raise AuthenticationError("Authentication credentials are invalid")

            return AuthenticatedIdentity.user(user.id, user.status)

        raise AuthenticationError("Authentication credentials are invalid")

    @staticmethod
    def _extract_token(authorization_header: str | None) -> str:
        if not authorization_header:
            raise AuthenticationError("Authentication credentials are required")

        scheme, separator, token = authorization_header.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            raise AuthenticationError("Authentication credentials are invalid")

        return token.strip()
