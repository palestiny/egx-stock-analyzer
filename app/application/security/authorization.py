from app.application.security.identity import AuthenticatedIdentity, Permission


class AuthorizationError(PermissionError):
    """Raised when an authenticated identity lacks a required permission."""


class OperatorAuthorizer:
    def require(self, identity: AuthenticatedIdentity, permission: Permission) -> None:
        if permission not in identity.permissions:
            raise AuthorizationError("Operator permission is required")
