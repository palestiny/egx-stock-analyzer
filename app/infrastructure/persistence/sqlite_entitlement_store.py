from datetime import datetime
from pathlib import Path
import sqlite3
from uuid import UUID

from app.application.subscriptions.entitlements import EntitlementStore
from app.domain.subscriptions.entitlement import EntitlementGrant
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteEntitlementStore(EntitlementStore):
    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS entitlement_grants (
                    grant_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    starts_at TEXT NOT NULL,
                    expires_at TEXT NULL,
                    granted_by TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    revoked_at TEXT NULL,
                    revoked_by TEXT NULL,
                    revoke_reason TEXT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_entitlement_user_capability
                ON entitlement_grants(user_id, capability, starts_at, expires_at)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS entitlement_audit (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grant_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    UNIQUE(grant_id, action, actor_id, occurred_at)
                )
                """
            )

    def grant(self, grant: EntitlementGrant) -> EntitlementGrant:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM entitlement_grants WHERE grant_id = ?",
                (str(grant.grant_id),),
            ).fetchone()
            if existing is not None:
                stored = self._to_grant(existing)
                if stored != grant:
                    raise ValueError("conflicting entitlement grant replay")
                return stored

            connection.execute(
                """
                INSERT INTO entitlement_grants(
                    grant_id, user_id, capability, starts_at, expires_at,
                    granted_by, reason, created_at, revoked_at, revoked_by, revoke_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._grant_values(grant),
            )
            connection.execute(
                """
                INSERT INTO entitlement_audit(grant_id, action, actor_id, occurred_at, reason)
                VALUES (?, 'GRANTED', ?, ?, ?)
                """,
                (
                    str(grant.grant_id),
                    str(grant.granted_by),
                    grant.created_at.isoformat(),
                    grant.reason,
                ),
            )
        return grant

    def revoke(
        self,
        grant_id: UUID,
        *,
        revoked_at: datetime,
        revoked_by: UUID,
        reason: str,
    ) -> EntitlementGrant | None:
        if revoked_at.tzinfo is None or revoked_at.utcoffset() is None:
            raise ValueError("revoked_at must be timezone-aware")
        if not reason.strip():
            raise ValueError("revocation reason is required")

        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM entitlement_grants WHERE grant_id = ?",
                (str(grant_id),),
            ).fetchone()
            if row is None:
                return None
            current = self._to_grant(row)
            if current.revoked_at is not None:
                if current.revoked_by == revoked_by and current.revoke_reason == reason:
                    return current
                raise ValueError("entitlement grant already revoked differently")

            connection.execute(
                """
                UPDATE entitlement_grants
                SET revoked_at = ?, revoked_by = ?, revoke_reason = ?
                WHERE grant_id = ? AND revoked_at IS NULL
                """,
                (revoked_at.isoformat(), str(revoked_by), reason, str(grant_id)),
            )
            connection.execute(
                """
                INSERT INTO entitlement_audit(grant_id, action, actor_id, occurred_at, reason)
                VALUES (?, 'REVOKED', ?, ?, ?)
                """,
                (str(grant_id), str(revoked_by), revoked_at.isoformat(), reason),
            )
            updated = connection.execute(
                "SELECT * FROM entitlement_grants WHERE grant_id = ?",
                (str(grant_id),),
            ).fetchone()
        if updated is None:
            raise RuntimeError("revoked entitlement grant disappeared")
        return self._to_grant(updated)

    def get(self, grant_id: UUID) -> EntitlementGrant | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM entitlement_grants WHERE grant_id = ?",
                (str(grant_id),),
            ).fetchone()
        return self._to_grant(row) if row is not None else None

    def for_user(self, user_id: UUID) -> tuple[EntitlementGrant, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM entitlement_grants
                WHERE user_id = ?
                ORDER BY starts_at ASC, grant_id ASC
                """,
                (str(user_id),),
            ).fetchall()
        return tuple(self._to_grant(row) for row in rows)

    @staticmethod
    def _grant_values(grant: EntitlementGrant) -> tuple[str | None, ...]:
        return (
            str(grant.grant_id),
            str(grant.user_id),
            grant.capability,
            grant.starts_at.isoformat(),
            grant.expires_at.isoformat() if grant.expires_at else None,
            str(grant.granted_by),
            grant.reason,
            grant.created_at.isoformat(),
            grant.revoked_at.isoformat() if grant.revoked_at else None,
            str(grant.revoked_by) if grant.revoked_by else None,
            grant.revoke_reason,
        )

    @staticmethod
    def _to_grant(row: tuple[object, ...]) -> EntitlementGrant:
        return EntitlementGrant(
            grant_id=UUID(str(row[0])),
            user_id=UUID(str(row[1])),
            capability=str(row[2]),
            starts_at=datetime.fromisoformat(str(row[3])),
            expires_at=datetime.fromisoformat(str(row[4])) if row[4] is not None else None,
            granted_by=UUID(str(row[5])),
            reason=str(row[6]),
            created_at=datetime.fromisoformat(str(row[7])),
            revoked_at=datetime.fromisoformat(str(row[8])) if row[8] is not None else None,
            revoked_by=UUID(str(row[9])) if row[9] is not None else None,
            revoke_reason=str(row[10]) if row[10] is not None else None,
        )
