from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable, TypeVar

from app.application.alerts.model import AlertEvent
from app.application.signals.lifecycle_unit_of_work import SignalLifecycleTransaction
from app.application.signals.store import SignalRecord
from app.domain.signals.model import Signal
from app.domain.signals.outcome import SignalOutcomeRecord
from app.infrastructure.notifications.sqlite_alert_outbox import SQLiteAlertOutbox
from app.infrastructure.persistence.sqlite_connection import connect_sqlite
from app.infrastructure.persistence.sqlite_signal_history_store import SQLiteSignalHistoryStore
from app.infrastructure.persistence.sqlite_track_record_store import SQLiteTrackRecordStore

T = TypeVar("T")


class _SQLiteSignalLifecycleTransaction(SignalLifecycleTransaction):
    def __init__(
        self,
        connection: sqlite3.Connection,
        history: SQLiteSignalHistoryStore,
        track_record: SQLiteTrackRecordStore,
        outbox: SQLiteAlertOutbox,
    ) -> None:
        self._connection = connection
        self._history = history
        self._track_record = track_record
        self._outbox = outbox

    def latest(self, symbol: str) -> SignalRecord | None:
        normalized = symbol.strip().upper()
        if not normalized:
            return None
        row = self._connection.execute(
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
        return self._history._to_record(row) if row else None

    def record_signal(
        self, signal: Signal, event: str, recorded_at
    ) -> SignalRecord:
        if not event.strip():
            raise ValueError("event is required")
        self._history._require_aware(recorded_at, "recorded_at")
        normalized_symbol = signal.symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("signal symbol is required")
        payload = self._history._serialize_signal(signal)
        identity = (
            normalized_symbol,
            signal.strategy_id,
            signal.strategy_version,
            signal.generated_at.isoformat(),
        )
        self._connection.execute(
            """
            INSERT OR IGNORE INTO signal_identities(
                signal_id, symbol, strategy_id, strategy_version, generated_at
            ) VALUES (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) ||
                      '-4' || substr(lower(hex(randomblob(2))), 2) || '-' ||
                      substr('89ab', abs(random()) % 4 + 1, 1) ||
                      substr(lower(hex(randomblob(2))), 2) || '-' ||
                      lower(hex(randomblob(6))), ?, ?, ?, ?)
            """,
            identity,
        )
        row = self._connection.execute(
            """
            SELECT signal_id FROM signal_identities
            WHERE symbol = ? AND strategy_id = ? AND strategy_version = ? AND generated_at = ?
            """,
            identity,
        ).fetchone()
        if row is None:
            raise RuntimeError("Signal identity was not persisted")
        signal_id = str(row[0])
        existing = self._connection.execute(
            """
            SELECT signal_json FROM signal_history
            WHERE signal_id = ? AND event = ? AND recorded_at = ?
            """,
            (signal_id, event.strip(), recorded_at.isoformat()),
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != payload:
                raise ValueError("different signal event already recorded")
            return SignalRecord(
                signal_id=self._history._to_record(
                    (signal_id, event.strip(), recorded_at.isoformat(), payload)
                ).signal_id,
                signal=signal,
                recorded_at=recorded_at,
                event=event.strip(),
            )
        self._connection.execute(
            """
            INSERT INTO signal_history(signal_id, event, recorded_at, signal_json)
            VALUES (?, ?, ?, ?)
            """,
            (signal_id, event.strip(), recorded_at.isoformat(), payload),
        )
        return SignalRecord(
            signal_id=self._history._to_record(
                (signal_id, event.strip(), recorded_at.isoformat(), payload)
            ).signal_id,
            signal=signal,
            recorded_at=recorded_at,
            event=event.strip(),
        )

    def record_outcome(self, outcome: SignalOutcomeRecord) -> None:
        payload = self._track_record._serialize(outcome)
        existing = self._connection.execute(
            "SELECT payload_json FROM signal_outcomes WHERE signal_id = ?",
            (str(outcome.signal_id),),
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != payload:
                raise ValueError("different outcome already recorded")
            return
        self._connection.execute(
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

    def publish_alert(self, event: AlertEvent) -> None:
        self._outbox._require_aware(event.occurred_at, "occurred_at")
        payload = self._outbox._serialize_event(event)
        existing = self._connection.execute(
            "SELECT event_json FROM signal_alert_outbox WHERE event_id = ?",
            (str(event.event_id),),
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != payload:
                raise ValueError("different alert event already recorded")
            return
        self._connection.execute(
            """
            INSERT INTO signal_alert_outbox(
                event_id, event_json, status, attempts, created_at
            ) VALUES (?, ?, 'PENDING', 0, ?)
            """,
            (str(event.event_id), payload, event.occurred_at.isoformat()),
        )


class SQLiteSignalLifecycleUnitOfWork:
    """One SQLite transaction for lifecycle history, optional outcome, and alert intent."""

    def __init__(
        self,
        history: SQLiteSignalHistoryStore,
        track_record: SQLiteTrackRecordStore,
        outbox: SQLiteAlertOutbox,
    ) -> None:
        paths = {
            Path(history._database_path).resolve(),
            Path(track_record._database_path).resolve(),
            Path(outbox._database_path).resolve(),
        }
        if len(paths) != 1:
            raise ValueError("lifecycle stores must share one SQLite database")
        self._database_path = str(next(iter(paths)))
        self._history = history
        self._track_record = track_record
        self._outbox = outbox

    def execute(self, operation: Callable[[SignalLifecycleTransaction], T]) -> T:
        connection = connect_sqlite(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            connection.execute("BEGIN IMMEDIATE")
            transaction = _SQLiteSignalLifecycleTransaction(
                connection,
                self._history,
                self._track_record,
                self._outbox,
            )
            result = operation(transaction)
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
