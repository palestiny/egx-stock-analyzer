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
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT user_id, verifier
                FROM user_credentials
                WHERE status = 'active'
                """
            ).fetchall()

        for raw_user_id, verifier in rows:
            if verify_secret(secret, verifier):
                return UUID(raw_user_id)

        return None

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
