from __future__ import annotations

import json
import sqlite3
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.application.alerts.outbox import AlertOutboxRecord, AlertOutboxStatus
from app.domain.alerts.model import (
    AlertEvent,
    AlertEventType,
    AlertEvidenceSnapshot,
    AlertSignalSnapshot,
    AlertTargetSnapshot,
)
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteAlertOutbox:
    """Persistent, idempotent outbox for domain alert events.

    This stores events before transport delivery. It intentionally does not claim
    atomicity with signal-history writes; that requires a shared transaction boundary.
    """

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
                CREATE TABLE IF NOT EXISTS signal_alert_outbox (
                    event_id TEXT PRIMARY KEY,
                    event_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    delivered_at TEXT NULL,
                    last_error TEXT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_signal_alert_outbox_pending
                ON signal_alert_outbox(status, created_at, event_id)
                """
            )

    def publish(self, event: AlertEvent) -> None:
        payload = self._serialize_event(event)
        self._require_aware(event.occurred_at, "occurred_at")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT event_json FROM signal_alert_outbox WHERE event_id = ?",
                (str(event.event_id),),
            ).fetchone()
            if row is not None:
                if str(row[0]) != payload:
                    raise ValueError("different alert event already recorded")
                return
            connection.execute(
                """
                INSERT INTO signal_alert_outbox(
                    event_id, event_json, status, attempts, created_at
                ) VALUES (?, ?, ?, 0, ?)
                """,
                (
                    str(event.event_id),
                    payload,
                    AlertOutboxStatus.PENDING.value,
                    event.occurred_at.isoformat(),
                ),
            )

    def pending(self, limit: int = 100) -> tuple[AlertOutboxRecord, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_json, status, attempts, created_at, delivered_at, last_error
                FROM signal_alert_outbox
                WHERE status IN (?, ?)
                ORDER BY created_at, event_id
                LIMIT ?
                """,
                (
                    AlertOutboxStatus.PENDING.value,
                    AlertOutboxStatus.FAILED.value,
                    limit,
                ),
            ).fetchall()
        return tuple(self._to_record(row) for row in rows)

    def get(self, event_id: UUID) -> AlertOutboxRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT event_json, status, attempts, created_at, delivered_at, last_error
                FROM signal_alert_outbox WHERE event_id = ?
                """,
                (str(event_id),),
            ).fetchone()
        return self._to_record(row) if row else None

    def mark_delivered(self, event_id: UUID, delivered_at: datetime) -> AlertOutboxRecord:
        self._require_aware(delivered_at, "delivered_at")
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE signal_alert_outbox
                SET status = ?, attempts = attempts + 1, delivered_at = ?, last_error = NULL
                WHERE event_id = ?
                """,
                (
                    AlertOutboxStatus.DELIVERED.value,
                    delivered_at.isoformat(),
                    str(event_id),
                ),
            )
        record = self.get(event_id)
        if record is None:
            raise LookupError("alert outbox event was not found")
        return record

    def mark_failed(self, event_id: UUID, error: str) -> AlertOutboxRecord:
        if not error.strip():
            raise ValueError("error is required")
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE signal_alert_outbox
                SET status = ?, attempts = attempts + 1, last_error = ?, delivered_at = NULL
                WHERE event_id = ?
                """,
                (AlertOutboxStatus.FAILED.value, error.strip(), str(event_id)),
            )
        record = self.get(event_id)
        if record is None:
            raise LookupError("alert outbox event was not found")
        return record

    def mark_suppressed_no_recipients(
        self,
        event_id: UUID,
        reason: str,
    ) -> AlertOutboxRecord:
        if not reason.strip():
            raise ValueError("suppression reason is required")
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE signal_alert_outbox
                SET status = ?, attempts = attempts + 1, last_error = ?, delivered_at = NULL
                WHERE event_id = ?
                """,
                (
                    AlertOutboxStatus.SUPPRESSED_NO_RECIPIENTS.value,
                    reason.strip(),
                    str(event_id),
                ),
            )
        record = self.get(event_id)
        if record is None:
            raise LookupError("alert outbox event was not found")
        return record

    def mark_suppressed_no_eligible_recipients(
        self,
        event_id: UUID,
        reason: str,
    ) -> AlertOutboxRecord:
        if not reason.strip():
            raise ValueError("suppression reason is required")
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE signal_alert_outbox
                SET status = ?, attempts = attempts + 1, last_error = ?, delivered_at = NULL
                WHERE event_id = ?
                """,
                (
                    AlertOutboxStatus.SUPPRESSED_NO_ELIGIBLE_RECIPIENTS.value,
                    reason.strip(),
                    str(event_id),
                ),
            )
        record = self.get(event_id)
        if record is None:
            raise LookupError("alert outbox event was not found")
        return record

    @staticmethod
    def _require_aware(value: datetime, field_name: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")

    @staticmethod
    def _serialize_event(event: AlertEvent) -> str:
        payload = {
            "event_id": str(event.event_id),
            "signal_id": str(event.signal_id),
            "symbol": event.symbol.strip().upper(),
            "event_type": event.event_type.value,
            "occurred_at": event.occurred_at.isoformat(),
            "message": event.message,
            "signal_snapshot": (
                {
                    "direction": event.signal_snapshot.direction,
                    "status": event.signal_snapshot.status,
                    "timeframe": event.signal_snapshot.timeframe,
                    "entry_lower": str(event.signal_snapshot.entry_lower),
                    "entry_upper": str(event.signal_snapshot.entry_upper),
                    "invalidation": str(event.signal_snapshot.invalidation),
                    "targets": [
                        {"price": str(item.price), "label": item.label}
                        for item in event.signal_snapshot.targets
                    ],
                    "evidence": [
                        {"kind": item.kind, "description": item.description}
                        for item in event.signal_snapshot.evidence
                    ],
                    "strategy_id": event.signal_snapshot.strategy_id,
                    "strategy_version": event.signal_snapshot.strategy_version,
                    "generated_at": event.signal_snapshot.generated_at.isoformat(),
                    "data_timestamp": event.signal_snapshot.data_timestamp.isoformat(),
                }
                if event.signal_snapshot is not None
                else None
            ),
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def _to_record(cls, row: tuple[object, ...]) -> AlertOutboxRecord:
        event = cls._deserialize_event(str(row[0]))
        return AlertOutboxRecord(
            event=event,
            status=AlertOutboxStatus(str(row[1])),
            attempts=int(str(row[2])),
            created_at=datetime.fromisoformat(str(row[3])),
            delivered_at=(
                datetime.fromisoformat(str(row[4])) if row[4] is not None else None
            ),
            last_error=str(row[5]) if row[5] is not None else None,
        )

    @staticmethod
    def _deserialize_event(payload_text: str) -> AlertEvent:
        payload = json.loads(payload_text)
        raw_snapshot = payload.get("signal_snapshot")
        snapshot = None
        if isinstance(raw_snapshot, dict):
            snapshot = AlertSignalSnapshot(
                direction=str(raw_snapshot["direction"]),
                status=str(raw_snapshot["status"]),
                timeframe=str(raw_snapshot["timeframe"]),
                entry_lower=Decimal(str(raw_snapshot["entry_lower"])),
                entry_upper=Decimal(str(raw_snapshot["entry_upper"])),
                invalidation=Decimal(str(raw_snapshot["invalidation"])),
                targets=tuple(
                    AlertTargetSnapshot(
                        price=Decimal(str(item["price"])),
                        label=str(item["label"]),
                    )
                    for item in raw_snapshot["targets"]
                ),
                evidence=tuple(
                    AlertEvidenceSnapshot(
                        kind=str(item["kind"]),
                        description=str(item["description"]),
                    )
                    for item in raw_snapshot["evidence"]
                ),
                strategy_id=str(raw_snapshot["strategy_id"]),
                strategy_version=str(raw_snapshot["strategy_version"]),
                generated_at=datetime.fromisoformat(str(raw_snapshot["generated_at"])),
                data_timestamp=datetime.fromisoformat(str(raw_snapshot["data_timestamp"])),
            )
        return AlertEvent(
            event_id=UUID(str(payload["event_id"])),
            signal_id=UUID(str(payload["signal_id"])),
            symbol=str(payload["symbol"]),
            event_type=AlertEventType(str(payload["event_type"])),
            occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
            message=str(payload["message"]),
            signal_snapshot=snapshot,
        )
