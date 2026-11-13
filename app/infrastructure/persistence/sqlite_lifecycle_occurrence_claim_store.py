from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from app.application.signals.occurrence_claims import (
    LifecycleOccurrenceClaim,
    LifecycleRetryPolicy,
)
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class StaleLifecycleOccurrenceClaimError(RuntimeError):
    """Raised when a worker tries to commit using an expired or superseded claim."""


class SQLiteLifecycleOccurrenceClaimStore:
    """Durable, fenced claims with immutable bounded retry policy per occurrence."""

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

    @staticmethod
    def _create_claim_table(connection: sqlite3.Connection, table_name: str) -> None:
        connection.execute(
            f"""
            CREATE TABLE {table_name} (
                occurrence_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                fencing_token INTEGER NOT NULL CHECK(fencing_token > 0),
                attempt INTEGER NOT NULL CHECK(attempt >= 0),
                status TEXT NOT NULL CHECK(status IN (
                    'CLAIMED', 'FAILED', 'COMPLETED', 'EXHAUSTED', 'LEGACY_BLOCKED'
                )),
                lease_until TEXT NULL,
                claimed_at TEXT NOT NULL,
                completed_at TEXT NULL,
                last_error TEXT NULL,
                retry_policy_json TEXT NULL,
                next_attempt_at TEXT NULL,
                exhausted_at TEXT NULL,
                recovery_generation INTEGER NOT NULL DEFAULT 0 CHECK(recovery_generation >= 0),
                legacy_lease_until TEXT NULL,
                CHECK(
                    (status = 'CLAIMED' AND lease_until IS NOT NULL AND completed_at IS NULL
                        AND exhausted_at IS NULL AND next_attempt_at IS NULL)
                    OR (status = 'FAILED' AND lease_until IS NULL AND completed_at IS NULL
                        AND exhausted_at IS NULL AND next_attempt_at IS NOT NULL)
                    OR (status = 'COMPLETED' AND lease_until IS NULL AND completed_at IS NOT NULL
                        AND exhausted_at IS NULL AND next_attempt_at IS NULL)
                    OR (status = 'EXHAUSTED' AND lease_until IS NULL AND completed_at IS NULL
                        AND exhausted_at IS NOT NULL AND next_attempt_at IS NULL)
                    OR (status = 'LEGACY_BLOCKED' AND lease_until IS NULL AND completed_at IS NULL
                        AND exhausted_at IS NULL AND next_attempt_at IS NULL)
                )
            )
            """
        )

    def _initialize(self) -> None:
        connection = connect_sqlite(self._database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' "
                "AND name = 'lifecycle_occurrence_claims'"
            ).fetchone()
            if existing is None:
                self._create_claim_table(connection, "lifecycle_occurrence_claims")
            else:
                columns = {
                    str(row[1])
                    for row in connection.execute(
                        "PRAGMA table_info(lifecycle_occurrence_claims)"
                    ).fetchall()
                }
                if "retry_policy_json" not in columns:
                    self._create_claim_table(connection, "lifecycle_occurrence_claims_v2")
                    connection.execute(
                        """
                        INSERT INTO lifecycle_occurrence_claims_v2(
                            occurrence_id, owner_id, fencing_token, attempt, status,
                            lease_until, claimed_at, completed_at, last_error,
                            retry_policy_json, next_attempt_at, exhausted_at,
                            recovery_generation, legacy_lease_until
                        )
                        SELECT occurrence_id, owner_id, fencing_token, attempt,
                            CASE WHEN status = 'COMPLETED' THEN 'COMPLETED'
                                 ELSE 'LEGACY_BLOCKED' END,
                            NULL, claimed_at, completed_at, last_error,
                            NULL, NULL, NULL, 0, lease_until
                        FROM lifecycle_occurrence_claims
                        """
                    )
                    connection.execute("DROP TABLE lifecycle_occurrence_claims")
                    connection.execute(
                        "ALTER TABLE lifecycle_occurrence_claims_v2 "
                        "RENAME TO lifecycle_occurrence_claims"
                    )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_lifecycle_occurrence_claims_status_lease
                ON lifecycle_occurrence_claims(status, lease_until, next_attempt_at)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS lifecycle_occurrence_claim_recoveries (
                    recovery_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurrence_id TEXT NOT NULL,
                    previous_status TEXT NOT NULL,
                    recovery_generation INTEGER NOT NULL,
                    actor_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    recovered_at TEXT NOT NULL,
                    retry_policy_json TEXT NOT NULL
                )
                """
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _validate_policy(policy: LifecycleRetryPolicy) -> str:
        if not isinstance(policy, LifecycleRetryPolicy):
            raise TypeError("retry_policy must be a LifecycleRetryPolicy")
        return policy.to_json()

    def claim(
        self,
        occurrence_id: str,
        owner_id: str,
        *,
        now: datetime,
        lease_seconds: int,
        retry_policy: LifecycleRetryPolicy,
    ) -> LifecycleOccurrenceClaim | None:
        if not occurrence_id.strip():
            raise ValueError("occurrence_id is required")
        if not owner_id.strip():
            raise ValueError("owner_id is required")
        if isinstance(lease_seconds, bool) or not isinstance(lease_seconds, int) or lease_seconds < 1:
            raise ValueError("lease_seconds must be a positive integer")
        policy_json = self._validate_policy(retry_policy)
        now_utc = self._aware_utc(now, "now")
        now_text = now_utc.isoformat()
        lease_until = now_utc + timedelta(seconds=lease_seconds)
        connection = connect_sqlite(self._database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT owner_id, fencing_token, attempt, status, lease_until,
                       retry_policy_json, next_attempt_at
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
                        lease_until, claimed_at, retry_policy_json
                    ) VALUES (?, ?, ?, ?, 'CLAIMED', ?, ?, ?)
                    """,
                    (
                        occurrence_id, owner_id, fencing_token, attempt,
                        lease_until.isoformat(), now_text, policy_json,
                    ),
                )
            else:
                status = str(row[3])
                stored_policy_json = str(row[5]) if row[5] is not None else None
                if status in ("COMPLETED", "EXHAUSTED", "LEGACY_BLOCKED"):
                    connection.rollback()
                    return None
                if stored_policy_json is None:
                    connection.execute(
                        """
                        UPDATE lifecycle_occurrence_claims
                        SET status = 'LEGACY_BLOCKED', lease_until = NULL,
                            next_attempt_at = NULL, legacy_lease_until = COALESCE(lease_until, legacy_lease_until)
                        WHERE occurrence_id = ?
                        """,
                        (occurrence_id,),
                    )
                    connection.commit()
                    return None
                stored_policy = LifecycleRetryPolicy.from_json(stored_policy_json)
                if stored_policy_json != policy_json or stored_policy != retry_policy:
                    raise ValueError("retry_policy cannot change during an occurrence")

                attempt = int(row[2])
                if status == "CLAIMED":
                    current_lease = (
                        datetime.fromisoformat(str(row[4])) if row[4] is not None else None
                    )
                    if current_lease is not None and self._aware_utc(
                        current_lease, "stored lease_until"
                    ) > now_utc:
                        connection.rollback()
                        return None
                    if attempt >= retry_policy.max_attempts:
                        connection.execute(
                            """
                            UPDATE lifecycle_occurrence_claims
                            SET status = 'EXHAUSTED', lease_until = NULL,
                                next_attempt_at = NULL, exhausted_at = ?,
                                last_error = 'claim lease expired after final attempt'
                            WHERE occurrence_id = ?
                            """,
                            (now_text, occurrence_id),
                        )
                        connection.commit()
                        return None
                    next_attempt_at = self._aware_utc(
                        current_lease, "stored lease_until"
                    ) + timedelta(seconds=retry_policy.delay_after(attempt))
                    if next_attempt_at > now_utc:
                        connection.execute(
                            """
                            UPDATE lifecycle_occurrence_claims
                            SET status = 'FAILED', lease_until = NULL,
                                next_attempt_at = ?, last_error = 'claim lease expired'
                            WHERE occurrence_id = ?
                            """,
                            (next_attempt_at.isoformat(), occurrence_id),
                        )
                        connection.commit()
                        return None
                    connection.execute(
                        """
                        UPDATE lifecycle_occurrence_claims
                        SET status = 'FAILED', lease_until = NULL,
                            next_attempt_at = ?, last_error = 'claim lease expired'
                        WHERE occurrence_id = ?
                        """,
                        (next_attempt_at.isoformat(), occurrence_id),
                    )
                    status = "FAILED"
                if status != "FAILED":
                    connection.rollback()
                    return None
                eligible_at = (
                    datetime.fromisoformat(str(row[6])) if row[6] is not None
                    else now_utc
                )
                if eligible_at > now_utc:
                    connection.rollback()
                    return None
                if attempt >= retry_policy.max_attempts:
                    connection.execute(
                        """
                        UPDATE lifecycle_occurrence_claims
                        SET status = 'EXHAUSTED', next_attempt_at = NULL, exhausted_at = ?,
                            last_error = COALESCE(last_error, 'retry budget exhausted')
                        WHERE occurrence_id = ?
                        """,
                        (now_text, occurrence_id),
                    )
                    connection.commit()
                    return None
                fencing_token = int(row[1]) + 1
                attempt = max(1, attempt + 1)
                connection.execute(
                    """
                    UPDATE lifecycle_occurrence_claims
                    SET owner_id = ?, fencing_token = ?, attempt = ?, status = 'CLAIMED',
                        lease_until = ?, claimed_at = ?, completed_at = NULL,
                        last_error = NULL, next_attempt_at = NULL, exhausted_at = NULL
                    WHERE occurrence_id = ?
                    """,
                    (
                        owner_id, fencing_token, attempt, lease_until.isoformat(),
                        now_text, occurrence_id,
                    ),
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

    def renew(
        self,
        claim: LifecycleOccurrenceClaim,
        *,
        now: datetime,
        lease_seconds: int,
    ) -> LifecycleOccurrenceClaim | None:
        """Extend a live claim only for its current owner and fencing token."""
        if isinstance(lease_seconds, bool) or not isinstance(lease_seconds, int) or lease_seconds < 1:
            raise ValueError("lease_seconds must be a positive integer")
        now_utc = self._aware_utc(now, "now")
        now_text = now_utc.isoformat()
        lease_until = now_utc + timedelta(seconds=lease_seconds)
        connection = connect_sqlite(self._database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE lifecycle_occurrence_claims
                SET lease_until = ?
                WHERE occurrence_id = ? AND owner_id = ? AND fencing_token = ?
                  AND status = 'CLAIMED' AND lease_until > ?
                """,
                (
                    lease_until.isoformat(), claim.occurrence_id, claim.owner_id,
                    claim.fencing_token, now_text,
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                return None
            connection.commit()
            return LifecycleOccurrenceClaim(
                occurrence_id=claim.occurrence_id,
                owner_id=claim.owner_id,
                fencing_token=claim.fencing_token,
                attempt=claim.attempt,
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
        failed_at_utc = self._aware_utc(failed_at, "failed_at")
        failed_at_text = failed_at_utc.isoformat()
        connection = connect_sqlite(self._database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT attempt, retry_policy_json FROM lifecycle_occurrence_claims
                WHERE occurrence_id = ? AND owner_id = ? AND fencing_token = ?
                  AND status = 'CLAIMED' AND lease_until > ?
                """,
                (claim.occurrence_id, claim.owner_id, claim.fencing_token, failed_at_text),
            ).fetchone()
            if row is None:
                connection.rollback()
                return False
            if row[1] is None:
                connection.execute(
                    """
                    UPDATE lifecycle_occurrence_claims
                    SET status = 'LEGACY_BLOCKED', lease_until = NULL,
                        legacy_lease_until = lease_until, next_attempt_at = NULL,
                        last_error = ?
                    WHERE occurrence_id = ?
                    """,
                    (reason.strip(), claim.occurrence_id),
                )
                connection.commit()
                return False
            attempt = int(row[0])
            policy = LifecycleRetryPolicy.from_json(str(row[1]))
            if attempt >= policy.max_attempts:
                cursor = connection.execute(
                    """
                    UPDATE lifecycle_occurrence_claims
                    SET status = 'EXHAUSTED', lease_until = NULL, next_attempt_at = NULL,
                        exhausted_at = ?, last_error = ?
                    WHERE occurrence_id = ? AND owner_id = ? AND fencing_token = ?
                    """,
                    (
                        failed_at_text, reason.strip(), claim.occurrence_id,
                        claim.owner_id, claim.fencing_token,
                    ),
                )
            else:
                next_attempt_at = failed_at_utc + timedelta(
                    seconds=policy.delay_after(attempt)
                )
                cursor = connection.execute(
                    """
                    UPDATE lifecycle_occurrence_claims
                    SET status = 'FAILED', lease_until = NULL, next_attempt_at = ?,
                        exhausted_at = NULL, last_error = ?
                    WHERE occurrence_id = ? AND owner_id = ? AND fencing_token = ?
                    """,
                    (
                        next_attempt_at.isoformat(), reason.strip(), claim.occurrence_id,
                        claim.owner_id, claim.fencing_token,
                    ),
                )
            connection.commit()
            return cursor.rowcount == 1
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def recover(
        self,
        occurrence_id: str,
        *,
        retry_policy: LifecycleRetryPolicy,
        actor_id: str,
        reason: str,
        recovered_at: datetime,
    ) -> bool:
        """Audited operator recovery for legacy-blocked or exhausted occurrences."""
        if not actor_id.strip():
            raise ValueError("recovery actor_id is required")
        if not reason.strip():
            raise ValueError("recovery reason is required")
        policy_json = self._validate_policy(retry_policy)
        recovered_text = self._timestamp(recovered_at, "recovered_at")
        connection = connect_sqlite(self._database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT status, recovery_generation FROM lifecycle_occurrence_claims
                WHERE occurrence_id = ?
                """,
                (occurrence_id,),
            ).fetchone()
            if row is None or str(row[0]) not in ("EXHAUSTED", "LEGACY_BLOCKED"):
                connection.rollback()
                return False
            previous_status = str(row[0])
            generation = int(row[1]) + 1
            connection.execute(
                """
                INSERT INTO lifecycle_occurrence_claim_recoveries(
                    occurrence_id, previous_status, recovery_generation,
                    actor_id, reason, recovered_at, retry_policy_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    occurrence_id, previous_status, generation, actor_id.strip(),
                    reason.strip(), recovered_text, policy_json,
                ),
            )
            cursor = connection.execute(
                """
                UPDATE lifecycle_occurrence_claims
                SET status = 'FAILED', attempt = 0, retry_policy_json = ?,
                    next_attempt_at = ?, lease_until = NULL, completed_at = NULL,
                    exhausted_at = NULL, recovery_generation = ?,
                    last_error = ?
                WHERE occurrence_id = ? AND status = ?
                """,
                (
                    policy_json, recovered_text, generation,
                    f"operator recovery: {reason.strip()}", occurrence_id, previous_status,
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
            SET status = 'COMPLETED', lease_until = NULL, completed_at = ?,
                last_error = NULL, next_attempt_at = NULL, exhausted_at = NULL
            WHERE occurrence_id = ? AND owner_id = ? AND fencing_token = ? AND status = 'CLAIMED'
            """,
            (
                cls._timestamp(completed_at, "completed_at"),
                claim.occurrence_id, claim.owner_id, claim.fencing_token,
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
                       lease_until, claimed_at, completed_at, last_error,
                       retry_policy_json, next_attempt_at, exhausted_at,
                       recovery_generation, legacy_lease_until
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
                "retry_policy": (
                    LifecycleRetryPolicy.from_json(str(row[9])) if row[9] else None
                ),
                "next_attempt_at": datetime.fromisoformat(str(row[10])) if row[10] else None,
                "exhausted_at": datetime.fromisoformat(str(row[11])) if row[11] else None,
                "recovery_generation": int(row[12]),
                "legacy_lease_until": datetime.fromisoformat(str(row[13])) if row[13] else None,
            }
        finally:
            connection.close()
