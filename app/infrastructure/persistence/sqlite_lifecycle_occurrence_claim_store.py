from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.application.signals.occurrence_claims import LifecycleOccurrenceClaim
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class StaleLifecycleOccurrenceClaimError(RuntimeError):
    """Raised when a worker tries to commit using an expired or superseded claim."""


class SQLiteLifecycleOccurrenceClaimStore:
    """Durable, fenced claims for lifecycle calendar/session/opportunity occurrences."""

    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path.resolve())
        self._initialize()

    @staticmethod
    def _aware_utc(value: datetime, field: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field} must be timezone-aware")
        return value.astimezone(timezone.utc)

    @classmethod
    def _timestamp(cls, value: datetime, field: str) -> str:
        return cls._aware_utc(value, field).isoformat()

    def _initialize(self) -> None:
        connection = connect_sqlite(self._database_path)
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS lifecycle_occurrence_claims (
                    occurrence_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    fencing_token INTEGER NOT NULL CHECK(fencing_token > 0),
                    attempt INTEGER NOT NULL CHECK(attempt > 0),
                    status TEXT NOT NULL CHECK(status IN ('CLAIMED', 'FAILED', 'COMPLETED')),
                    lease_until TEXT NULL,
                    claimed_at TEXT NOT NULL,
                    completed_at TEXT NULL,
                    last_error TEXT NULL,
                    CHECK(
                        (status = 'CLAIMED' AND lease_until IS NOT NULL AND completed_at IS NULL)
                        OR (status = 'FAILED' AND lease_until IS NULL AND completed_at IS NULL)
                        OR (status = 'COMPLETED' AND lease_until IS NULL AND completed_at IS NOT NULL)
                    )
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_lifecycle_occurrence_claims_status_lease
                ON lifecycle_occurrence_claims(status, lease_until)
                """
            )
            connection.commit()
        finally:
            connection.close()

    def claim(
        self,
        occurrence_id: str,
        owner_id: str,
        *,
        now: datetime,
        lease_seconds: int,
    ) -> LifecycleOccurrenceClaim | None:
        if not occurrence_id.strip():
            raise ValueError("occurrence_id is required")
        if not owner_id.strip():
            raise ValueError("owner_id is required")
        if isinstance(lease_seconds, bool) or not isinstance(lease_seconds, int) or lease_seconds < 1:
            raise ValueError("lease_seconds must be a positive integer")
        now_utc = self._aware_utc(now, "now")
        now_text = now_utc.isoformat()
        lease_until = now_utc + timedelta(seconds=lease_seconds)
        connection = connect_sqlite(self._database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT owner_id, fencing_token, attempt, status, lease_until
                FROM lifecycle_occurrence_claims
                WHERE occurrence_id = ?
                """,
                (occurrence_id,),
            ).fetchone()
            if row is None:
                fencing_token = 1
                attempt = 1
                connection.execute(
                    """
                    INSERT INTO lifecycle_occurrence_claims(
                        occurrence_id, owner_id, fencing_token, attempt, status,
                        lease_until, claimed_at
                    ) VALUES (?, ?, ?, ?, 'CLAIMED', ?, ?)
                    """,
                    (occurrence_id, owner_id, fencing_token, attempt, lease_until.isoformat(), now_text),
                )
            else:
                status = str(row[3])
                current_lease = (
                    datetime.fromisoformat(str(row[4]))
                    if row[4] is not None
                    else None
                )
                if status == "COMPLETED" or (
                    status == "CLAIMED"
                    and current_lease is not None
                    and self._aware_utc(current_lease, "stored lease_until") > now_utc
                ):
                    connection.rollback()
                    return None
                fencing_token = int(row[1]) + 1
                attempt = int(row[2]) + 1
                connection.execute(
                    """
                    UPDATE lifecycle_occurrence_claims
                    SET owner_id = ?, fencing_token = ?, attempt = ?, status = 'CLAIMED',
                        lease_until = ?, claimed_at = ?, completed_at = NULL, last_error = NULL
                    WHERE occurrence_id = ?
                    """,
                    (owner_id, fencing_token, attempt, lease_until.isoformat(), now_text, occurrence_id),
                )
            connection.commit()
            return LifecycleOccurrenceClaim(
                occurrence_id=occurrence_id,
                owner_id=owner_id,
                fencing_token=fencing_token,
                attempt=attempt,
                lease_until=lease_until,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_failed(
        self,
        claim: LifecycleOccurrenceClaim,
        *,
        failed_at: datetime,
        reason: str,
    ) -> bool:
        if not reason.strip():
            raise ValueError("failure reason is required")
        failed_at_text = self._timestamp(failed_at, "failed_at")
        connection = connect_sqlite(self._database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE lifecycle_occurrence_claims
                SET status = 'FAILED', lease_until = NULL, last_error = ?
                WHERE occurrence_id = ? AND owner_id = ? AND fencing_token = ?
                  AND status = 'CLAIMED' AND lease_until > ?
                """,
                (
                    reason.strip(),
                    claim.occurrence_id,
                    claim.owner_id,
                    claim.fencing_token,
                    failed_at_text,
                ),
            )
            connection.commit()
            return cursor.rowcount == 1
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @classmethod
    def assert_current_claim(
        cls,
        connection: sqlite3.Connection,
        claim: LifecycleOccurrenceClaim,
        *,
        now: datetime,
    ) -> None:
        if not connection.in_transaction:
            raise RuntimeError("claim validation requires the lifecycle write transaction")
        now_text = cls._timestamp(now, "now")
        row = connection.execute(
            """
            SELECT owner_id, fencing_token, status, lease_until
            FROM lifecycle_occurrence_claims
            WHERE occurrence_id = ?
            """,
            (claim.occurrence_id,),
        ).fetchone()
        if (
            row is None
            or str(row[0]) != claim.owner_id
            or int(row[1]) != claim.fencing_token
            or str(row[2]) != "CLAIMED"
            or row[3] is None
            or str(row[3]) <= now_text
        ):
            raise StaleLifecycleOccurrenceClaimError(
                "lifecycle occurrence claim is missing, expired, or fenced by a newer owner"
            )

    @classmethod
    def complete_claim(
        cls,
        connection: sqlite3.Connection,
        claim: LifecycleOccurrenceClaim,
        *,
        completed_at: datetime,
    ) -> None:
        cls.assert_current_claim(connection, claim, now=completed_at)
        cursor = connection.execute(
            """
            UPDATE lifecycle_occurrence_claims
            SET status = 'COMPLETED', lease_until = NULL, completed_at = ?, last_error = NULL
            WHERE occurrence_id = ? AND owner_id = ? AND fencing_token = ? AND status = 'CLAIMED'
            """,
            (
                cls._timestamp(completed_at, "completed_at"),
                claim.occurrence_id,
                claim.owner_id,
                claim.fencing_token,
            ),
        )
        if cursor.rowcount != 1:
            raise StaleLifecycleOccurrenceClaimError(
                "lifecycle occurrence claim changed before completion"
            )

    def get(self, occurrence_id: str) -> dict[str, object] | None:
        connection = connect_sqlite(self._database_path)
        try:
            row = connection.execute(
                """
                SELECT occurrence_id, owner_id, fencing_token, attempt, status,
                       lease_until, claimed_at, completed_at, last_error
                FROM lifecycle_occurrence_claims WHERE occurrence_id = ?
                """,
                (occurrence_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "occurrence_id": str(row[0]),
                "owner_id": str(row[1]),
                "fencing_token": int(row[2]),
                "attempt": int(row[3]),
                "status": str(row[4]),
                "lease_until": datetime.fromisoformat(str(row[5])) if row[5] else None,
                "claimed_at": datetime.fromisoformat(str(row[6])),
                "completed_at": datetime.fromisoformat(str(row[7])) if row[7] else None,
                "last_error": str(row[8]) if row[8] is not None else None,
            }
        finally:
            connection.close()
