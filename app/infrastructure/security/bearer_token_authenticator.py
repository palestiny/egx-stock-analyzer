from secrets import compare_digest

from app.application.security.identity import AuthenticatedIdentity


class AuthenticationError(ValueError):
    """Raised when bearer authentication cannot establish an identity."""


class BearerTokenAuthenticator:
    def __init__(self, expected_token: str) -> None:
        if not expected_token.strip():
            raise ValueError("Operator token must be configured")
        self._expected_token = expected_token

    def authenticate(self, authorization_header: str | None) -> AuthenticatedIdentity:
        token = self._extract_token(authorization_header)
        if token is None or not compare_digest(token, self._expected_token):
            raise AuthenticationError("Invalid authentication credentials")
        return AuthenticatedIdentity.operator()

    @staticmethod
    def _extract_token(authorization_header: str | None) -> str | None:
        if not authorization_header:
            return None

        scheme, separator, token = authorization_header.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            return None

        return token.strip()
