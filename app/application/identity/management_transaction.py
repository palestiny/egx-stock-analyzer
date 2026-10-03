from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.application.identity.management_audit import ManagementAuditEvent
from app.application.security.credentials import PreparedCredential
from app.domain.identity.user import User


class ManagementMutationTransaction(Protocol):
    """Atomic boundary for management mutations and their audit event."""

    def create_user(
        self,
        user: User,
        credential: PreparedCredential,
        event: ManagementAuditEvent,
    ) -> None:
        ...

    def set_user_status(
        self,
        user: User,
        event: ManagementAuditEvent,
    ) -> None:
        ...

    def rotate_credential(
        self,
        credential_id: UUID,
        user_id: UUID,
        replacement: PreparedCredential,
        revoked_at: datetime,
        event: ManagementAuditEvent,
    ) -> None:
        ...
