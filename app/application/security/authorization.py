from app.application.security.identity import (
    AuthenticatedIdentity,
    Permission,
)


class AuthorizationError(PermissionError):
    """Raised when an authenticated identity lacks a required permission."""


def require_permission(
    identity: AuthenticatedIdentity,
    permission: Permission,
) -> None:
    if permission not in identity.permissions:
        raise AuthorizationError("Required permission is not available")
