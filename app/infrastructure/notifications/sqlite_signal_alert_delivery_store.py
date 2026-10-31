from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.application.alerts.telegram_delivery_store import (
    SignalAlertDeliveryRecord,
    SignalAlertDeliveryStatus,
    SignalAlertDeliveryStore,
)
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteSignalAlertDeliveryStore(SignalAlertDeliveryStore):
    """Durable per-recipient delivery state with atomic, fenced claims."""

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
                CREATE TABLE IF NOT EXISTS signal_alert_deliveries (
                    event_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_error TEXT NULL,
                    claim_token TEXT NULL,
                    lease_until TEXT NULL,
                    PRIMARY KEY(event_id, user_id, channel)
                )
                """
            )
            columns = {
                str(row[1])
                for row in connection.execute(
                    "PRAGMA table_info(signal_alert_deliveries)"
                ).fetchall()
            }
            if "claim_token" not in columns:
                connection.execute(
                    "ALTER TABLE signal_alert_deliveries ADD COLUMN claim_token TEXT NULL"
                )
            if "lease_until" not in columns:
                connection.execute(
                    "ALTER TABLE signal_alert_deliveries ADD COLUMN lease_until TEXT NULL"
                )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_signal_alert_delivery_status
                ON signal_alert_deliveries(status, updated_at)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_signal_alert_delivery_lease
                ON signal_alert_deliveries(status, lease_until)
                """
            )

    def get(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
    ) -> SignalAlertDeliveryRecord | None:
        normalized_channel = self._normalize_channel(channel)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT event_id, user_id, channel, status, attempts,
                    created_at, updated_at, last_error, claim_token, lease_until
                FROM signal_alert_deliveries
                WHERE event_id = ? AND user_id = ? AND channel = ?
                """,
                (str(event_id), str(user_id), normalized_channel),
            ).fetchone()
        return self._to_record(row) if row else None

    def create_pending(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        now: datetime,
    ) -> SignalAlertDeliveryRecord:
        self._require_aware(now, "now")
        normalized_channel = self._normalize_channel(channel)
        now_text = self._timestamp(now)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO signal_alert_deliveries(
                    event_id, user_id, channel, status, attempts, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    str(event_id),
                    str(user_id),
                    normalized_channel,
                    SignalAlertDeliveryStatus.PENDING.value,
                    now_text,
                    now_text,
                ),
            )
        record = self.get(event_id, user_id, normalized_channel)
        if record is None:
            raise RuntimeError("Signal alert delivery was not persisted")
        return record

    def claim(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        claim_token: UUID,
        now: datetime,
        lease_until: datetime,
    ) -> bool:
        self._require_aware(now, "now")
        self._require_aware(lease_until, "lease_until")
        now_text = self._timestamp(now)
        lease_text = self._timestamp(lease_until)
        if lease_until.astimezone(timezone.utc) <= now.astimezone(timezone.utc):
            raise ValueError("lease_until must be later than now")
        key = (str(event_id), str(user_id), self._normalize_channel(channel))
        # BEGIN IMMEDIATE serializes competing claim writers before the conditional
        # update. The network call is never made inside this transaction.
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE signal_alert_deliveries
                SET status = ?, claim_token = NULL, lease_until = NULL,
                    updated_at = ?, last_error = COALESCE(last_error, ?)
                WHERE event_id = ? AND user_id = ? AND channel = ?
                  AND status = ? AND lease_until <= ?
                """,
                (
                    SignalAlertDeliveryStatus.DELIVERY_UNKNOWN.value,
                    now_text,
                    "send outcome unknown after claim lease expired",
                    *key,
                    SignalAlertDeliveryStatus.SENDING.value,
                    now_text,
                ),
            )
            connection.execute(
                """
                UPDATE signal_alert_deliveries
                SET status = ?, claim_token = NULL, lease_until = NULL, updated_at = ?
                WHERE event_id = ? AND user_id = ? AND channel = ?
                  AND status = ? AND lease_until <= ?
                """,
                (
                    SignalAlertDeliveryStatus.PENDING.value,
                    now_text,
                    *key,
                    SignalAlertDeliveryStatus.CLAIMED.value,
                    now_text,
                ),
            )
            cursor = connection.execute(
                """
                UPDATE signal_alert_deliveries
                SET status = ?, claim_token = ?, lease_until = ?, updated_at = ?
                WHERE event_id = ? AND user_id = ? AND channel = ?
                  AND status IN (?, ?)
                """,
                (
                    SignalAlertDeliveryStatus.CLAIMED.value,
                    str(claim_token),
                    lease_text,
                    now_text,
                    *key,
                    SignalAlertDeliveryStatus.PENDING.value,
                    SignalAlertDeliveryStatus.FAILED.value,
                ),
            )
            return cursor.rowcount == 1

    def mark_sending(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        claim_token: UUID,
        now: datetime,
    ) -> bool:
        self._require_aware(now, "now")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE signal_alert_deliveries
                SET status = ?, attempts = attempts + 1, updated_at = ?
                WHERE event_id = ? AND user_id = ? AND channel = ?
                  AND status = ? AND claim_token = ? AND lease_until > ?
                """,
                (
                    SignalAlertDeliveryStatus.SENDING.value,
                    self._timestamp(now),
                    str(event_id),
                    str(user_id),
                    self._normalize_channel(channel),
                    SignalAlertDeliveryStatus.CLAIMED.value,
                    str(claim_token),
                    self._timestamp(now),
                ),
            )
        return cursor.rowcount == 1

    def complete_delivered(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        claim_token: UUID,
        now: datetime,
    ) -> bool:
        return self._complete_claimed(
            event_id, user_id, channel, claim_token=claim_token,
            status=SignalAlertDeliveryStatus.DELIVERED, now=now, error=None,
        )

    def complete_failed(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        error: str,
        *,
        claim_token: UUID,
        now: datetime,
    ) -> bool:
        if not error.strip():
            raise ValueError("delivery error is required")
        return self._complete_claimed(
            event_id, user_id, channel, claim_token=claim_token,
            status=SignalAlertDeliveryStatus.FAILED, now=now, error=error.strip(),
        )

    def mark_delivery_unknown(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        reason: str,
        *,
        claim_token: UUID,
        now: datetime,
    ) -> bool:
        if not reason.strip():
            raise ValueError("unknown delivery reason is required")
        return self._complete_claimed(
            event_id, user_id, channel, claim_token=claim_token,
            status=SignalAlertDeliveryStatus.DELIVERY_UNKNOWN,
            now=now, error=reason.strip(),
        )

    def _complete_claimed(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        claim_token: UUID,
        status: SignalAlertDeliveryStatus,
        now: datetime,
        error: str | None,
    ) -> bool:
        self._require_aware(now, "now")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE signal_alert_deliveries
                SET status = ?, updated_at = ?, last_error = ?,
                    claim_token = NULL, lease_until = NULL
                WHERE event_id = ? AND user_id = ? AND channel = ?
                  AND status = ? AND claim_token = ? AND lease_until > ?
                """,
                (
                    status.value,
                    self._timestamp(now),
                    error,
                    str(event_id),
                    str(user_id),
                    self._normalize_channel(channel),
                    SignalAlertDeliveryStatus.SENDING.value,
                    str(claim_token),
                    self._timestamp(now),
                ),
            )
        return cursor.rowcount == 1

    def recover_expired_claims(self, *, now: datetime) -> int:
        self._require_aware(now, "now")
        now_text = self._timestamp(now)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            unknown = connection.execute(
                """
                UPDATE signal_alert_deliveries
                SET status = ?, claim_token = NULL, lease_until = NULL,
                    updated_at = ?, last_error = ?
                WHERE status = ? AND lease_until <= ?
                """,
                (
                    SignalAlertDeliveryStatus.DELIVERY_UNKNOWN.value,
                    now_text,
                    "send outcome unknown after claim lease expired",
                    SignalAlertDeliveryStatus.SENDING.value,
                    now_text,
                ),
            )
            reclaimed = connection.execute(
                """
                UPDATE signal_alert_deliveries
                SET status = ?, claim_token = NULL, lease_until = NULL,
                    updated_at = ?, last_error = NULL
                WHERE status = ? AND lease_until <= ?
                """,
                (
                    SignalAlertDeliveryStatus.PENDING.value,
                    now_text,
                    SignalAlertDeliveryStatus.CLAIMED.value,
                    now_text,
                ),
            )
        return unknown.rowcount + reclaimed.rowcount

    def mark_delivered(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        now: datetime,
    ) -> SignalAlertDeliveryRecord:
        return self._update(
            event_id, user_id, channel,
            status=SignalAlertDeliveryStatus.DELIVERED, now=now,
            increment_attempts=True, last_error=None,
        )

    def mark_failed(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        error: str,
        *,
        now: datetime,
    ) -> SignalAlertDeliveryRecord:
        if not error.strip():
            raise ValueError("delivery error is required")
        return self._update(
            event_id, user_id, channel,
            status=SignalAlertDeliveryStatus.FAILED, now=now,
            increment_attempts=True, last_error=error.strip(),
        )

    def mark_suppressed(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        reason: str,
        *,
        now: datetime,
    ) -> SignalAlertDeliveryRecord:
        if not reason.strip():
            raise ValueError("suppression reason is required")
        return self._update(
            event_id, user_id, channel,
            status=SignalAlertDeliveryStatus.SUPPRESSED, now=now,
            increment_attempts=False, last_error=reason.strip(),
        )

    def _update(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        status: SignalAlertDeliveryStatus,
        now: datetime,
        increment_attempts: bool,
        last_error: str | None,
    ) -> SignalAlertDeliveryRecord:
        self._require_aware(now, "now")
        normalized_channel = self._normalize_channel(channel)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE signal_alert_deliveries
                SET status = ?, attempts = attempts + ?, updated_at = ?, last_error = ?
                WHERE event_id = ? AND user_id = ? AND channel = ?
                """,
                (
                    status.value, int(increment_attempts), self._timestamp(now),
                    last_error, str(event_id), str(user_id), normalized_channel,
                ),
            )
            if cursor.rowcount != 1:
                raise LookupError("Signal alert delivery record was not found")
        record = self.get(event_id, user_id, normalized_channel)
        if record is None:
            raise RuntimeError("Signal alert delivery record disappeared")
        return record

    @staticmethod
    def _normalize_channel(channel: str) -> str:
        normalized = channel.strip().lower()
        if not normalized:
            raise ValueError("delivery channel is required")
        return normalized

    @staticmethod
    def _require_aware(value: datetime, field_name: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")

    @classmethod
    def _timestamp(cls, value: datetime) -> str:
        cls._require_aware(value, "timestamp")
        return value.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _to_record(row: tuple[object, ...]) -> SignalAlertDeliveryRecord:
        return SignalAlertDeliveryRecord(
            event_id=UUID(str(row[0])),
            user_id=UUID(str(row[1])),
            channel=str(row[2]),
            status=SignalAlertDeliveryStatus(str(row[3])),
            attempts=int(str(row[4])),
            created_at=datetime.fromisoformat(str(row[5])),
            updated_at=datetime.fromisoformat(str(row[6])),
            last_error=str(row[7]) if row[7] is not None else None,
            claim_token=UUID(str(row[8])) if row[8] is not None else None,
            lease_until=datetime.fromisoformat(str(row[9])) if row[9] is not None else None,
        )
