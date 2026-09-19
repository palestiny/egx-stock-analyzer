from app.application.security.identity import AuthenticatedIdentity


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
            raise AuthenticationError("Invalid authentication credentials")

        if token.strip() != self._expected_token:
            raise AuthenticationError("Invalid authentication credentials")

        return AuthenticatedIdentity.operator()
