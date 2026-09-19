from app.application.security.identity import AuthenticatedIdentity, Permission


class AuthenticationError(ValueError):
    """Raised when bearer credentials are missing or invalid."""


class BearerTokenAuthenticator:
    def __init__(self, token: str) -> None:
        normalized = token.strip()
        if not normalized:
            raise ValueError("Operator token cannot be empty")
        self._token = normalized

    def authenticate(self, authorization_header: str | None) -> AuthenticatedIdentity:
        if not authorization_header:
            raise AuthenticationError("Authentication required")

        scheme, separator, credentials = authorization_header.partition(" ")
        if separator != " " or scheme.lower() != "bearer" or not credentials.strip():
            raise AuthenticationError("Invalid authentication credentials")

        if credentials.strip() != self._token:
            raise AuthenticationError("Invalid authentication credentials")

        return AuthenticatedIdentity(permission=Permission.OPERATOR)
