from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.application.identity.management_audit import ManagementAuditEvent, ManagementAuditStore
from app.application.identity.user_store import UserStore
from app.application.security.authorization import AuthorizationError, OperatorAuthorizer, OwnershipAuthorizer
from app.application.security.credentials import CredentialService, IssuedCredential
from app.application.security.identity import AuthenticatedIdentity, Permission, LEGACY_OPERATOR_USER_ID
from app.domain.identity.user import User, UserStatus

class UserManagementError(ValueError):
    pass

class UserManagementService:
    def __init__(
        self,
        user_store: UserStore,
        credential_service: CredentialService,
        audit_store: ManagementAuditStore,
    ) -> None:
        self._users = user_store
        self._credentials = credential_service
        self._audit = audit_store
        self._operator = OperatorAuthorizer()
        self._ownership = OwnershipAuthorizer()

    def create_user(self, actor: AuthenticatedIdentity) -> tuple[User, IssuedCredential]:
        self._operator.require(actor, Permission.OPERATOR)
        user = User(id=uuid4(), status=UserStatus.ACTIVE)
        credential = self._credentials.provision(user.id)
        self._users.save(user)
        self._record(actor, "user_created", user.id, "success")
        return user, credential

    def set_status(
        self,
        actor: AuthenticatedIdentity,
        user_id: UUID,
        status: UserStatus,
    ) -> User:
        self._operator.require(actor, Permission.OPERATOR)
        user = self._users.get(user_id)
        if user is None:
            raise UserManagementError("User not found")
        if user.status is status:
            raise UserManagementError("Invalid user lifecycle transition")
        if user.id == LEGACY_OPERATOR_USER_ID and status is not UserStatus.ACTIVE:
            raise UserManagementError("Legacy operator cannot be disabled or deleted")
        if user.status is UserStatus.DELETED:
            raise UserManagementError("Deleted user cannot be reactivated or disabled")
        if status not in {UserStatus.DISABLED, UserStatus.DELETED, UserStatus.ACTIVE}:
            raise UserManagementError("Unsupported user status")
        updated = User(id=user.id, status=status)
        self._users.save(updated)
        self._record(actor, f"user_{status.value}", user.id, "success")
        return updated

    def rotate_own_credential(
        self,
        actor: AuthenticatedIdentity,
    ) -> IssuedCredential:
        self._ownership.require_authenticated(actor)
        if actor.credential_id is None:
            raise UserManagementError("Self-service credential rotation is unavailable for this credential")
        assert actor.user_id is not None
        issued = self._credentials.rotate(actor.credential_id, actor.user_id)
        self._record(actor, "credential_rotated", actor.user_id, "success")
        return issued

    def rotate_user_credential(
        self,
        actor: AuthenticatedIdentity,
        user_id: UUID,
    ) -> IssuedCredential:
        self._operator.require(actor, Permission.OPERATOR)
        user = self._users.get(user_id)
        if user is None:
            raise UserManagementError("User not found")
        if user.status is UserStatus.DELETED:
            raise UserManagementError("Deleted user cannot receive credentials")
        issued = self._credentials.rotate_latest_for_user(user_id)
        self._record(actor, "credential_rotated_by_operator", user_id, "success")
        return issued

    def _record(
        self,
        actor: AuthenticatedIdentity,
        action: str,
        target_user_id: UUID,
        outcome: str,
    ) -> None:
        if actor.user_id is None:
            raise AuthorizationError("Authenticated user identity is required")
        self._audit.append(
            ManagementAuditEvent(
                actor_user_id=actor.user_id,
                action=action,
                target_user_id=target_user_id,
                occurred_at=datetime.now(timezone.utc),
                outcome=outcome,
            )
        )
