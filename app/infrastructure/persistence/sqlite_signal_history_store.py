from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from app.application.signals.store import SignalRecord, SignalHistoryStore
from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteSignalHistoryStore(SignalHistoryStore):
    """Durable signal identity and append-only signal history backed by SQLite."""

    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = connect_sqlite(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_identities (
                    signal_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    strategy_version TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    UNIQUE(symbol, strategy_id, strategy_version, generated_at)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    signal_json TEXT NOT NULL,
                    UNIQUE(signal_id, event, recorded_at),
                    FOREIGN KEY(signal_id) REFERENCES signal_identities(signal_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_signal_history_timeline
                ON signal_history(signal_id, id)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_signal_identity_symbol
                ON signal_identities(symbol)
                """
            )

    def record(self, signal: Signal, event: str, recorded_at: datetime) -> SignalRecord:
        if not event.strip():
            raise ValueError("event is required")
        self._require_aware(recorded_at, "recorded_at")
        normalized_symbol = signal.symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("signal symbol is required")
        payload = self._serialize_signal(signal)
        identity = (
            normalized_symbol,
            signal.strategy_id,
            signal.strategy_version,
            signal.generated_at.isoformat(),
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO signal_identities(
                    signal_id, symbol, strategy_id, strategy_version, generated_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid4()), *identity),
            )
            row = connection.execute(
                """
                SELECT signal_id FROM signal_identities
                WHERE symbol = ? AND strategy_id = ? AND strategy_version = ? AND generated_at = ?
                """,
                identity,
            ).fetchone()
            if row is None:
                raise RuntimeError("Signal identity was not persisted")
            signal_id = UUID(str(row[0]))
            existing = connection.execute(
                """
                SELECT signal_json FROM signal_history
                WHERE signal_id = ? AND event = ? AND recorded_at = ?
                """,
                (str(signal_id), event.strip(), recorded_at.isoformat()),
            ).fetchone()
            if existing is not None:
                if str(existing[0]) != payload:
                    raise ValueError("different signal event already recorded")
                return SignalRecord(signal_id, signal, recorded_at, event.strip())

            connection.execute(
                """
                INSERT INTO signal_history(signal_id, event, recorded_at, signal_json)
                VALUES (?, ?, ?, ?)
                """,
                (str(signal_id), event.strip(), recorded_at.isoformat(), payload),
            )
        return SignalRecord(signal_id, signal, recorded_at, event.strip())

    def get(self, signal_id: UUID) -> SignalRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT signal_id, event, recorded_at, signal_json
                FROM signal_history
                WHERE signal_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (str(signal_id),),
            ).fetchone()
        return self._to_record(row) if row else None

    def history(self, signal_id: UUID) -> tuple[SignalRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT signal_id, event, recorded_at, signal_json
                FROM signal_history
                WHERE signal_id = ?
                ORDER BY id ASC
                """,
                (str(signal_id),),
            ).fetchall()
        return tuple(self._to_record(row) for row in rows)

    def latest(self, symbol: str) -> SignalRecord | None:
        normalized = symbol.strip().upper()
        if not normalized:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT h.signal_id, h.event, h.recorded_at, h.signal_json
                FROM signal_history h
                JOIN signal_identities i ON i.signal_id = h.signal_id
                WHERE i.symbol = ?
                ORDER BY h.id DESC
                LIMIT 1
                """,
                (normalized,),
            ).fetchone()
        return self._to_record(row) if row else None

    @staticmethod
    def _require_aware(value: datetime, field_name: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")

    @staticmethod
    def _serialize_signal(signal: Signal) -> str:
        payload = {
            "symbol": signal.symbol.strip().upper(),
            "direction": signal.direction.value,
            "status": signal.status.value,
            "generated_at": signal.generated_at.isoformat(),
            "timeframe": signal.timeframe,
            "entry_zone": {
                "lower": str(signal.entry_zone.lower),
                "upper": str(signal.entry_zone.upper),
            },
            "invalidation": str(signal.invalidation),
            "targets": [
                {"price": str(target.price), "label": target.label}
                for target in signal.targets
            ],
            "confidence": str(signal.confidence),
            "risk_score": str(signal.risk_score),
            "evidence": [
                {
                    "kind": evidence.kind,
                    "description": evidence.description,
                    "weight": str(evidence.weight),
                }
                for evidence in signal.evidence
            ],
            "strategy_id": signal.strategy_id,
            "strategy_version": signal.strategy_version,
            "data_timestamp": signal.data_timestamp.isoformat(),
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def _to_record(cls, row: tuple[object, ...]) -> SignalRecord:
        return SignalRecord(
            signal_id=UUID(str(row[0])),
            event=str(row[1]),
            recorded_at=datetime.fromisoformat(str(row[2])),
            signal=cls._deserialize_signal(str(row[3])),
        )

    @staticmethod
    def _deserialize_signal(payload_text: str) -> Signal:
        payload = json.loads(payload_text)
        return Signal(
            symbol=str(payload["symbol"]),
            direction=SignalDirection(str(payload["direction"])),
            status=SignalStatus(str(payload["status"])),
            generated_at=datetime.fromisoformat(str(payload["generated_at"])),
            timeframe=str(payload["timeframe"]),
            entry_zone=PriceZone(
                lower=Decimal(str(payload["entry_zone"]["lower"])),
                upper=Decimal(str(payload["entry_zone"]["upper"])),
            ),
            invalidation=Decimal(str(payload["invalidation"])),
            targets=tuple(
                Target(price=Decimal(str(item["price"])), label=str(item["label"]))
                for item in payload["targets"]
            ),
            confidence=Decimal(str(payload["confidence"])),
            risk_score=Decimal(str(payload["risk_score"])),
            evidence=tuple(
                SignalEvidence(
                    kind=str(item["kind"]),
                    description=str(item["description"]),
                    weight=Decimal(str(item["weight"])),
                )
                for item in payload["evidence"]
            ),
            strategy_id=str(payload["strategy_id"]),
            strategy_version=str(payload["strategy_version"]),
            data_timestamp=datetime.fromisoformat(str(payload["data_timestamp"])),
        )
