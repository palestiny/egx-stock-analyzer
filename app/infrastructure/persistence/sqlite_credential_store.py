import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.application.security.credentials import (
    CredentialStore,
    StoredCredential,
    verify_secret,
)


class SQLiteCredentialStore(CredentialStore):
    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_credentials (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verifier TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    revoked_at TEXT NULL,
                    replaced_by TEXT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_credentials_user_id ON user_credentials(user_id)"
            )

    def create(self, credential: StoredCredential, verifier: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_credentials
                    (id, user_id, status, verifier, created_at, revoked_at, replaced_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(credential.id),
                    str(credential.user_id),
                    credential.status,
                    verifier,
                    credential.created_at.isoformat(),
                    credential.revoked_at.isoformat() if credential.revoked_at else None,
                    str(credential.replaced_by) if credential.replaced_by else None,
                ),
            )

    def find_active_user_id(self, secret: str) -> UUID | None:
        credential = self.find_active_credential(secret)
        return credential.user_id if credential is not None else None

    def find_active_credential(self, secret: str) -> StoredCredential | None:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, user_id, status, created_at, revoked_at, replaced_by, verifier
                FROM user_credentials
                WHERE status = 'active'
                """
            ).fetchall()

        for raw_id, raw_user_id, status, created_at, revoked_at, replaced_by, verifier in rows:
            if verify_secret(secret, verifier):
                return StoredCredential(
                    id=UUID(raw_id),
                    user_id=UUID(raw_user_id),
                    status=status,
                    created_at=datetime.fromisoformat(created_at),
                    revoked_at=datetime.fromisoformat(revoked_at) if revoked_at else None,
                    replaced_by=UUID(replaced_by) if replaced_by else None,
                )
        return None

    def find_active_for_user(self, user_id: UUID) -> list[StoredCredential]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, user_id, status, created_at, revoked_at, replaced_by
                FROM user_credentials
                WHERE user_id = ? AND status = 'active'
                ORDER BY created_at ASC, id ASC
                """,
                (str(user_id),),
            ).fetchall()
        return [
            StoredCredential(
                id=UUID(row[0]),
                user_id=UUID(row[1]),
                status=row[2],
                created_at=datetime.fromisoformat(row[3]),
                revoked_at=datetime.fromisoformat(row[4]) if row[4] else None,
                replaced_by=UUID(row[5]) if row[5] else None,
            )
            for row in rows
        ]

    def replace(
        self,
        credential_id: UUID,
        user_id: UUID,
        replacement: StoredCredential,
        replacement_verifier: str,
        revoked_at: datetime,
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
                    str(replacement.id),
                    str(replacement.user_id),
                    replacement.status,
                    replacement_verifier,
                    replacement.created_at.isoformat(),
                    None,
                    None,
                ),
            )
            connection.execute(
                """
                UPDATE user_credentials
                SET status = 'replaced', revoked_at = ?, replaced_by = ?
                WHERE id = ?
                """,
                (revoked_at.isoformat(), str(replacement.id), str(credential_id)),
            )

    def revoke(
        self,
        credential_id: UUID,
        revoked_at: datetime,
        replacement_id: UUID | None = None,
    ) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE user_credentials
                SET status = ?, revoked_at = ?, replaced_by = ?
                WHERE id = ? AND status = 'active'
                """,
                (
                    "replaced" if replacement_id is not None else "revoked",
                    revoked_at.isoformat(),
                    str(replacement_id) if replacement_id else None,
                    str(credential_id),
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError("Credential is missing or already inactive")
