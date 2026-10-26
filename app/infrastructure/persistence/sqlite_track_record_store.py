from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.application.signals.track_record import TrackRecordStore
from app.domain.signals.model import SignalDirection
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteTrackRecordStore(TrackRecordStore):
    """Durable, idempotent storage for terminal signal outcomes."""

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
                CREATE TABLE IF NOT EXISTS signal_outcomes (
                    signal_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    strategy_version TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_signal_outcomes_strategy
                ON signal_outcomes(strategy_id, strategy_version, observed_at)
                """
            )

    def record(self, outcome: SignalOutcomeRecord) -> None:
        payload = self._serialize(outcome)
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT payload_json FROM signal_outcomes WHERE signal_id = ?",
                (str(outcome.signal_id),),
            ).fetchone()
            if existing is not None:
                if str(existing[0]) != payload:
                    raise ValueError("different outcome already recorded")
                return
            connection.execute(
                """
                INSERT INTO signal_outcomes(
                    signal_id, symbol, outcome, strategy_id, strategy_version,
                    observed_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(outcome.signal_id),
                    outcome.symbol.strip().upper(),
                    outcome.outcome.value,
                    outcome.strategy_id,
                    outcome.strategy_version,
                    outcome.observed_at.isoformat(),
                    payload,
                ),
            )

    def get(self, signal_id: UUID) -> SignalOutcomeRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM signal_outcomes WHERE signal_id = ?",
                (str(signal_id),),
            ).fetchone()
        return self._deserialize(str(row[0])) if row else None

    def all(self) -> tuple[SignalOutcomeRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM signal_outcomes
                ORDER BY observed_at, signal_id
                """
            ).fetchall()
        return tuple(self._deserialize(str(row[0])) for row in rows)

    @staticmethod
    def _serialize(outcome: SignalOutcomeRecord) -> str:
        payload = {
            "signal_id": str(outcome.signal_id),
            "symbol": outcome.symbol.strip().upper(),
            "outcome": outcome.outcome.value,
            "direction": outcome.direction.value,
            "observed_at": outcome.observed_at.isoformat(),
            "entry_price": str(outcome.entry_price),
            "exit_price": str(outcome.exit_price),
            "realized_return": str(outcome.realized_return),
            "realized_r": str(outcome.realized_r),
            "invalidation": str(outcome.invalidation),
            "target_label": outcome.target_label,
            "strategy_id": outcome.strategy_id,
            "strategy_version": outcome.strategy_version,
            "data_timestamp": outcome.data_timestamp.isoformat(),
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _deserialize(payload_text: str) -> SignalOutcomeRecord:
        payload = json.loads(payload_text)
        return SignalOutcomeRecord(
            signal_id=UUID(str(payload["signal_id"])),
            symbol=str(payload["symbol"]),
            outcome=SignalOutcome(str(payload["outcome"])),
            direction=SignalDirection(str(payload["direction"])),
            observed_at=datetime.fromisoformat(str(payload["observed_at"])),
            entry_price=Decimal(str(payload["entry_price"])),
            exit_price=Decimal(str(payload["exit_price"])),
            realized_return=Decimal(str(payload["realized_return"])),
            realized_r=Decimal(str(payload["realized_r"])),
            invalidation=Decimal(str(payload["invalidation"])),
            target_label=(
                str(payload["target_label"])
                if payload["target_label"] is not None
                else None
            ),
            strategy_id=str(payload["strategy_id"]),
            strategy_version=str(payload["strategy_version"]),
            data_timestamp=datetime.fromisoformat(str(payload["data_timestamp"])),
        )
