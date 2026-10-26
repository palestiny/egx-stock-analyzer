from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.application.alerts.telegram_delivery_store import (
    SignalAlertDeliveryRecord,
    SignalAlertDeliveryStatus,
    SignalAlertDeliveryStore,
)
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteSignalAlertDeliveryStore(SignalAlertDeliveryStore):
    """Idempotent per-event, per-user Telegram delivery state."""

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
                    PRIMARY KEY(event_id, user_id, channel)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_signal_alert_delivery_status
                ON signal_alert_deliveries(status, updated_at)
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
                    created_at, updated_at, last_error
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
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
        record = self.get(event_id, user_id, normalized_channel)
        if record is None:
            raise RuntimeError("Signal alert delivery was not persisted")
        return record

    def mark_delivered(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        now: datetime,
    ) -> SignalAlertDeliveryRecord:
        return self._update(
            event_id,
            user_id,
            channel,
            status=SignalAlertDeliveryStatus.DELIVERED,
            now=now,
            increment_attempts=True,
            last_error=None,
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
            event_id,
            user_id,
            channel,
            status=SignalAlertDeliveryStatus.FAILED,
            now=now,
            increment_attempts=True,
            last_error=error.strip(),
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
            event_id,
            user_id,
            channel,
            status=SignalAlertDeliveryStatus.SUPPRESSED,
            now=now,
            increment_attempts=False,
            last_error=reason.strip(),
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
                    status.value,
                    int(increment_attempts),
                    now.isoformat(),
                    last_error,
                    str(event_id),
                    str(user_id),
                    normalized_channel,
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
        )
