from uuid import UUID

from app.application.security.identity import AuthenticatedIdentity, Permission
from app.domain.identity.user import UserStatus


class AuthorizationError(PermissionError):
    """Raised when an authenticated identity lacks required access."""


class OperatorAuthorizer:
    def require(self, identity: AuthenticatedIdentity, permission: Permission) -> None:
        if permission not in identity.permissions:
            raise AuthorizationError("Operator permission is required")


class OwnershipAuthorizer:
    def require_authenticated(self, identity: AuthenticatedIdentity) -> None:
        if identity.user_id is None:
            raise AuthorizationError("Authenticated user identity is required")
        if identity.user_status is not UserStatus.ACTIVE:
            raise AuthorizationError("User is not active")

    def require_owner(
        self,
        identity: AuthenticatedIdentity,
        owner_user_id: UUID,
    ) -> None:
        self.require_authenticated(identity)
        if identity.user_id != owner_user_id:
            raise AuthorizationError("Resource is owned by another user")

    def require_global_access(self, identity: AuthenticatedIdentity) -> None:
        self.require_authenticated(identity)
        if Permission.OPERATOR not in identity.permissions:
            raise AuthorizationError("Operator permission is required for global resources")

    def require_owner_or_global(
        self,
        identity: AuthenticatedIdentity,
        owner_user_id: UUID | None,
    ) -> None:
        if owner_user_id is None:
            self.require_global_access(identity)
            return
        self.require_owner(identity, owner_user_id)
