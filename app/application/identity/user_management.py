from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.application.identity.management_audit import ManagementAuditEvent, ManagementAuditStore
from app.application.identity.management_transaction import ManagementMutationTransaction
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
        transaction: ManagementMutationTransaction,
    ) -> None:
        self._users = user_store
        self._credentials = credential_service
        self._audit = audit_store
        self._transaction = transaction
        self._operator = OperatorAuthorizer()
        self._ownership = OwnershipAuthorizer()

    def list_users(self, actor: AuthenticatedIdentity) -> list[User]:
        self._operator.require(actor, Permission.OPERATOR)
        return self._users.list()

    def create_user(self, actor: AuthenticatedIdentity) -> tuple[User, IssuedCredential]:
        self._operator.require(actor, Permission.OPERATOR)
        user = User(id=uuid4(), status=UserStatus.ACTIVE)
        prepared = self._credentials.prepare_provision(user.id)
        self._transaction.create_user(
            user,
            prepared,
            self._event(actor, "user_created", user.id),
        )
        return user, prepared.issued

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
        self._transaction.set_user_status(
            updated,
            self._event(actor, f"user_{status.value}", user.id),
        )
        return updated

    def rotate_own_credential(
        self,
        actor: AuthenticatedIdentity,
    ) -> IssuedCredential:
        self._ownership.require_authenticated(actor)
        if actor.credential_id is None:
            raise UserManagementError("Self-service credential rotation is unavailable for this credential")
        assert actor.user_id is not None
        prepared, revoked_at = self._credentials.prepare_rotation(actor.credential_id, actor.user_id)
        self._transaction.rotate_credential(
            actor.credential_id,
            actor.user_id,
            prepared,
            revoked_at,
            self._event(actor, "credential_rotated", actor.user_id),
        )
        return prepared.issued

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
        try:
            active = self._credentials._store.find_active_for_user(user_id)
            if not active:
                raise ValueError("No durable credential is available for this user")
            prepared, revoked_at = self._credentials.prepare_rotation(active[-1].id, user_id)
            self._transaction.rotate_credential(
                active[-1].id,
                user_id,
                prepared,
                revoked_at,
                self._event(actor, "credential_rotated_by_operator", user_id),
            )
            return prepared.issued
        except ValueError as error:
            raise UserManagementError(str(error)) from error

    @staticmethod
    def _event(
        actor: AuthenticatedIdentity,
        action: str,
        target_user_id: UUID,
    ) -> ManagementAuditEvent:
        if actor.user_id is None:
            raise AuthorizationError("Authenticated user identity is required")
        return ManagementAuditEvent(
            actor_user_id=actor.user_id,
            action=action,
            target_user_id=target_user_id,
            occurred_at=datetime.now(timezone.utc),
            outcome="success",
        )
