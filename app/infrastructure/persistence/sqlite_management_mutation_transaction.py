import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Callable
from uuid import UUID

from app.application.identity.management_audit import ManagementAuditEvent
from app.application.identity.management_transaction import ManagementMutationTransaction
from app.application.security.credentials import PreparedCredential
from app.domain.identity.user import User


class SQLiteManagementMutationTransaction(ManagementMutationTransaction):
    """Single-connection SQLite transaction for user/credential/audit mutations."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        audit_failure_hook: Callable[[], None] | None = None,
    ) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._audit_failure_hook = audit_failure_hook

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def create_user(
        self,
        user: User,
        credential: PreparedCredential,
        event: ManagementAuditEvent,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO users (id, status) VALUES (?, ?)",
                (str(user.id), user.status.value),
            )
            connection.execute(
                """
                INSERT INTO user_credentials
                    (id, user_id, status, verifier, created_at, revoked_at, replaced_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(credential.stored.id),
                    str(credential.stored.user_id),
                    credential.stored.status,
                    credential.verifier,
                    credential.stored.created_at.isoformat(),
                    None,
                    None,
                ),
            )
            self._append_audit(connection, event)

    def set_user_status(self, user: User, event: ManagementAuditEvent) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE users SET status = ? WHERE id = ?",
                (user.status.value, str(user.id)),
            )
            if cursor.rowcount != 1:
                raise ValueError("User not found")
            self._append_audit(connection, event)

    def rotate_credential(
        self,
        credential_id: UUID,
        user_id: UUID,
        replacement: PreparedCredential,
        revoked_at: datetime,
        event: ManagementAuditEvent,
    ) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT user_id, status FROM user_credentials WHERE id = ?",
                (str(credential_id),),
            ).fetchone()
            if row is None or row[1] != "active" or UUID(row[0]) != user_id:
                raise ValueError("Credential is missing, inactive, or owned by another user")

            connection.execute(
                """
                INSERT INTO user_credentials
                    (id, user_id, status, verifier, created_at, revoked_at, replaced_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(replacement.stored.id),
                    str(replacement.stored.user_id),
                    replacement.stored.status,
                    replacement.verifier,
                    replacement.stored.created_at.isoformat(),
                    None,
                    None,
                ),
            )
            connection.execute(
                """
                UPDATE user_credentials
                SET status = 'replaced', revoked_at = ?, replaced_by = ?
                WHERE id = ? AND status = 'active'
                """,
                (revoked_at.isoformat(), str(replacement.stored.id), str(credential_id)),
            )
            self._append_audit(connection, event)

    def _append_audit(
        self,
        connection: sqlite3.Connection,
        event: ManagementAuditEvent,
    ) -> None:
        if self._audit_failure_hook is not None:
            self._audit_failure_hook()
        connection.execute(
            """
            INSERT INTO management_audit
                (actor_user_id, action, target_user_id, occurred_at, outcome)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(event.actor_user_id),
                event.action,
                str(event.target_user_id),
                event.occurred_at.isoformat(),
                event.outcome,
            ),
        )
