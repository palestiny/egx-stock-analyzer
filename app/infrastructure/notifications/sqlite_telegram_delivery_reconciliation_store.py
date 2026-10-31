from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.application.alerts.telegram_delivery_reconciliation import (
    TelegramDeliveryReconciliation,
    TelegramDeliveryReconciliationStore,
)
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteTelegramDeliveryReconciliationStore(TelegramDeliveryReconciliationStore):
    """Operator-only reconciliation with an atomic state change and audit append."""

    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_delivery_reconciliation_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    previous_status TEXT NOT NULL,
                    new_status TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    actor_subject TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._database_path)

    def list_unresolved(self, *, limit: int = 50, offset: int = 0) -> tuple[dict[str, object], ...]:
        self._validate_page(limit, offset)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, user_id, channel, status, attempts,
                       created_at, updated_at
                FROM signal_alert_deliveries
                WHERE status IN ('FAILED', 'DELIVERY_UNKNOWN')
                ORDER BY updated_at ASC, event_id, user_id
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return tuple({
            "event_id": str(row[0]),
            "user_id": str(row[1]),
            "channel": str(row[2]),
            "status": str(row[3]),
            "attempts": int(row[4]),
            "created_at": str(row[5]),
            "updated_at": str(row[6]),
        } for row in rows)

    def reconcile(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        outcome: str,
        actor_subject: str,
        reason: str,
        now: datetime,
    ) -> TelegramDeliveryReconciliation:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        if not actor_subject.strip():
            raise ValueError("actor identity is required")
        if not reason.strip():
            raise ValueError("reconciliation reason is required")
        normalized_channel = channel.strip().lower()
        if not normalized_channel:
            raise ValueError("channel is required")
        targets = {
            "CONFIRMED_DELIVERED": "DELIVERED",
            "CONFIRMED_NOT_DELIVERED": "NOT_DELIVERED",
        }
        if outcome not in targets:
            raise ValueError("unsupported reconciliation outcome")
        timestamp = now.astimezone(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT status FROM signal_alert_deliveries
                WHERE event_id = ? AND user_id = ? AND channel = ?
                """,
                (str(event_id), str(user_id), normalized_channel),
            ).fetchone()
            if row is None:
                raise LookupError("delivery record not found")
            previous_status = str(row[0])
            if previous_status not in {"FAILED", "DELIVERY_UNKNOWN"}:
                raise ValueError("delivery record is not eligible for manual reconciliation")
            new_status = targets[outcome]
            cursor = connection.execute(
                """
                UPDATE signal_alert_deliveries
                SET status = ?, updated_at = ?, last_error = ?,
                    claim_token = NULL, lease_until = NULL
                WHERE event_id = ? AND user_id = ? AND channel = ?
                  AND status = ?
                """,
                (
                    new_status,
                    timestamp,
                    None if new_status == "DELIVERED" else f"operator confirmed not delivered: {reason.strip()}",
                    str(event_id),
                    str(user_id),
                    normalized_channel,
                    previous_status,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError("delivery state changed; refresh before reconciling")
            connection.execute(
                """
                INSERT INTO telegram_delivery_reconciliation_audit(
                    event_id, user_id, channel, previous_status, new_status,
                    outcome, actor_subject, reason, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event_id), str(user_id), normalized_channel,
                    previous_status, new_status, outcome, actor_subject.strip(),
                    reason.strip(), timestamp,
                ),
            )
        return TelegramDeliveryReconciliation(
            event_id, user_id, normalized_channel, previous_status, new_status,
            outcome, actor_subject.strip(), reason.strip(), datetime.fromisoformat(timestamp),
        )

    def list_audit(self, *, limit: int = 50, offset: int = 0) -> tuple[TelegramDeliveryReconciliation, ...]:
        self._validate_page(limit, offset)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, user_id, channel, previous_status, new_status,
                       outcome, actor_subject, reason, occurred_at
                FROM telegram_delivery_reconciliation_audit
                ORDER BY id DESC LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return tuple(
            TelegramDeliveryReconciliation(
                UUID(row[0]), UUID(row[1]), row[2], row[3], row[4],
                row[5], row[6], row[7], datetime.fromisoformat(row[8]),
            )
            for row in rows
        )

    @staticmethod
    def _validate_page(limit: int, offset: int) -> None:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        if offset < 0:
            raise ValueError("offset must not be negative")
