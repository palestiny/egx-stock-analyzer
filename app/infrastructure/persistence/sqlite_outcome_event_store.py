from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable, Iterable
from uuid import UUID

from app.application.signals.outcome_event_store import InMemoryOutcomeEventStore
from app.domain.signals.model import SignalDirection
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord
from app.domain.signals.outcome_event import (
    OutcomeCorrectionDecision,
    OutcomeEvent,
    OutcomeEventKind,
)
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteOutcomeEventStore:
    """Durable append-only outcome events with transactional state validation."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._clock = clock
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_outcome_events (
                    event_id TEXT PRIMARY KEY,
                    signal_id TEXT NOT NULL,
                    event_kind TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_credential_id TEXT,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    outcome_json TEXT,
                    supersedes_event_id TEXT,
                    decision TEXT
                )
                """
            )
            columns = {
                row[1] for row in connection.execute(
                    "PRAGMA table_info(signal_outcome_events)"
                ).fetchall()
            }
            if "actor_credential_id" not in columns:
                connection.execute(
                    "ALTER TABLE signal_outcome_events ADD COLUMN actor_credential_id TEXT"
                )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_signal_outcome_events_signal_time
                ON signal_outcome_events(signal_id, recorded_at, event_id)
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_signal_outcome_events_no_update
                BEFORE UPDATE ON signal_outcome_events
                BEGIN
                    SELECT RAISE(ABORT, 'signal outcome events are append-only');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_signal_outcome_events_no_delete
                BEFORE DELETE ON signal_outcome_events
                BEGIN
                    SELECT RAISE(ABORT, 'signal outcome events are append-only');
                END
                """
            )

    def _execute(self, operation, *, signal_ids: tuple[UUID, ...] | None = None):
        if signal_ids == ():
            return operation(InMemoryOutcomeEventStore(clock=self._clock))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            query = """
                SELECT event_id, signal_id, event_kind, recorded_at, actor_id,
                       idempotency_key, outcome_json, supersedes_event_id, decision,
                       actor_credential_id
                FROM signal_outcome_events
            """
            parameters: tuple[str, ...] = ()
            # Stay below SQLite's conservative host-parameter limit. For very
            # large batches, one full ordered scan is safer than an oversized IN.
            if signal_ids is not None and len(signal_ids) <= 900:
                placeholders = ", ".join("?" for _ in signal_ids)
                query += f" WHERE signal_id IN ({placeholders})"
                parameters = tuple(str(signal_id) for signal_id in signal_ids)
            query += " ORDER BY rowid"
            rows = connection.execute(query, parameters).fetchall()
            memory = InMemoryOutcomeEventStore(clock=self._clock)
            for row in rows:
                event = self._deserialize_event(row)
                memory._events.append(event)
                memory._idempotency[event.idempotency_key] = event
            previous_count = len(memory._events)
            result = operation(memory)
            if len(memory._events) > previous_count:
                event = memory._events[-1]
                connection.execute(
                    """
                    INSERT INTO signal_outcome_events(
                        event_id, signal_id, event_kind, recorded_at, actor_id,
                        idempotency_key, outcome_json, supersedes_event_id, decision,
                        actor_credential_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(event.event_id),
                        str(event.signal_id),
                        event.kind.value,
                        event.recorded_at.isoformat(),
                        event.actor_id,
                        event.idempotency_key,
                        self._serialize_outcome(event.outcome) if event.outcome else None,
                        str(event.supersedes_event_id) if event.supersedes_event_id else None,
                        event.decision.value if event.decision else None,
                        str(event.actor_credential_id) if event.actor_credential_id else None,
                    ),
                )
            return result

    def record_initial(
        self, outcome: SignalOutcomeRecord, *, actor_id: str, idempotency_key: str,
        actor_credential_id: UUID | None = None,
    ) -> OutcomeEvent:
        return self._execute(
            lambda store: store.record_initial(
                outcome, actor_id=actor_id, idempotency_key=idempotency_key,
                actor_credential_id=actor_credential_id,
            )
        )

    def submit_correction(
        self,
        outcome: SignalOutcomeRecord,
        *,
        supersedes_event_id: UUID,
        actor_id: str,
        idempotency_key: str,
        actor_credential_id: UUID | None = None,
    ) -> OutcomeEvent:
        return self._execute(
            lambda store: store.submit_correction(
                outcome,
                supersedes_event_id=supersedes_event_id,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                actor_credential_id=actor_credential_id,
            )
        )

    def review_correction(
        self,
        correction_event_id: UUID,
        *,
        reviewer_id: str,
        decision: OutcomeCorrectionDecision,
        idempotency_key: str,
        reviewer_credential_id: UUID | None = None,
    ) -> OutcomeEvent:
        return self._execute(
            lambda store: store.review_correction(
                correction_event_id,
                reviewer_id=reviewer_id,
                decision=decision,
                idempotency_key=idempotency_key,
                reviewer_credential_id=reviewer_credential_id,
            )
        )

    def outcome_as_of(
        self, signal_id: UUID, *, cutoff: datetime
    ) -> OutcomeEvent | None:
        return self._execute(lambda store: store.outcome_as_of(signal_id, cutoff=cutoff))

    def outcomes_as_of(
        self, signal_ids: Iterable[UUID], *, cutoff: datetime
    ) -> dict[UUID, OutcomeEvent]:
        unique_signal_ids = tuple(dict.fromkeys(signal_ids))
        if not unique_signal_ids:
            return {}
        return self._execute(
            lambda store: store.outcomes_as_of(unique_signal_ids, cutoff=cutoff),
            signal_ids=unique_signal_ids,
        )

    def events_for(self, signal_id: UUID) -> tuple[OutcomeEvent, ...]:
        return self._execute(lambda store: store.events_for(signal_id))

    @staticmethod
    def _serialize_outcome(outcome: SignalOutcomeRecord) -> str:
        payload = {
            "signal_id": str(outcome.signal_id),
            "symbol": outcome.symbol,
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
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _deserialize_outcome(payload_text: str) -> SignalOutcomeRecord:
        payload = json.loads(payload_text)
        return SignalOutcomeRecord(
            signal_id=UUID(payload["signal_id"]),
            symbol=payload["symbol"],
            outcome=SignalOutcome(payload["outcome"]),
            direction=SignalDirection(payload["direction"]),
            observed_at=datetime.fromisoformat(payload["observed_at"]),
            entry_price=Decimal(payload["entry_price"]),
            exit_price=Decimal(payload["exit_price"]),
            realized_return=Decimal(payload["realized_return"]),
            realized_r=Decimal(payload["realized_r"]),
            invalidation=Decimal(payload["invalidation"]),
            target_label=payload["target_label"],
            strategy_id=payload["strategy_id"],
            strategy_version=payload["strategy_version"],
            data_timestamp=datetime.fromisoformat(payload["data_timestamp"]),
        )

    @classmethod
    def _deserialize_event(cls, row) -> OutcomeEvent:
        return OutcomeEvent(
            event_id=UUID(row[0]),
            signal_id=UUID(row[1]),
            kind=OutcomeEventKind(row[2]),
            recorded_at=datetime.fromisoformat(row[3]),
            actor_id=row[4],
            idempotency_key=row[5],
            outcome=cls._deserialize_outcome(row[6]) if row[6] else None,
            supersedes_event_id=UUID(row[7]) if row[7] else None,
            decision=OutcomeCorrectionDecision(row[8]) if row[8] else None,
            actor_credential_id=UUID(row[9]) if row[9] else None,
        )
