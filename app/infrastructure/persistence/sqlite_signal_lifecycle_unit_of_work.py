from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable, TypeVar
from uuid import UUID, uuid4

from app.application.signals.lifecycle_unit_of_work import (
    LifecycleCorrectionRecord,
    LifecycleSessionGapEvent,
    LifecycleObservationRecord,
    SignalLifecycleTransaction,
)
from app.application.signals.store import SignalRecord
from app.domain.alerts.model import AlertEvent
from app.domain.signals.lifecycle import CompletedDailyBarObservation
from app.domain.signals.model import Signal, SignalStatus
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

    def get_observation(self, signal_id: UUID, identity):
        key = json.dumps(
            [identity[0], identity[1], identity[2], identity[3].isoformat(), identity[4]],
            separators=(",", ":"),
        )
        row = self._connection.execute(
            "SELECT payload_json FROM signal_lifecycle_daily_observations WHERE identity_key = ? AND signal_id = ?",
            (key, str(signal_id)),
        ).fetchone()
        return self._deserialize_observation(str(row[0])) if row else None

    def latest_observation(self, signal_id: UUID):
        row = self._connection.execute(
            """
            SELECT payload_json FROM signal_lifecycle_daily_observations
            WHERE signal_id = ?
            ORDER BY candle_at DESC, observed_at DESC
            LIMIT 1
            """,
            (str(signal_id),),
        ).fetchone()
        return self._deserialize_observation(str(row[0])) if row else None

    def record_session_gap_event(self, event: LifecycleSessionGapEvent) -> None:
        existing = self._connection.execute(
            """
            SELECT gap_id, signal_id, session_date, calendar_version, status, reason
            FROM signal_lifecycle_session_gap_events WHERE event_id = ?
            """,
            (str(event.event_id),),
        ).fetchone()
        if existing is not None:
            expected = (
                str(event.gap_id),
                str(event.signal_id),
                event.session_date.isoformat(),
                event.calendar_version,
                event.status,
                event.reason,
            )
            if tuple(str(value) for value in existing) != expected:
                raise ValueError("conflicting lifecycle session-gap event replay")
            return
        self._connection.execute(
            """
            INSERT INTO signal_lifecycle_session_gap_events(
                event_id, gap_id, signal_id, session_date,
                calendar_version, status, reason, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(event.event_id),
                str(event.gap_id),
                str(event.signal_id),
                event.session_date.isoformat(),
                event.calendar_version,
                event.status,
                event.reason,
                event.recorded_at.isoformat(),
            ),
        )

    def session_gap_events(self, signal_id: UUID) -> tuple[LifecycleSessionGapEvent, ...]:
        rows = self._connection.execute(
            """
            SELECT event_id, gap_id, signal_id, session_date,
                   calendar_version, status, reason, recorded_at
            FROM signal_lifecycle_session_gap_events
            WHERE signal_id = ?
            ORDER BY session_date ASC, recorded_at ASC, event_id ASC
            """,
            (str(signal_id),),
        ).fetchall()
        return tuple(
            LifecycleSessionGapEvent(
                event_id=UUID(str(row[0])),
                gap_id=UUID(str(row[1])),
                signal_id=UUID(str(row[2])),
                session_date=date.fromisoformat(str(row[3])),
                calendar_version=str(row[4]),
                status=str(row[5]),
                reason=str(row[6]),
                recorded_at=datetime.fromisoformat(str(row[7])),
            )
            for row in rows
        )

    def record_correction(self, record: LifecycleCorrectionRecord) -> None:
        original_key = json.dumps(
            [
                record.original_identity[0],
                record.original_identity[1],
                record.original_identity[2],
                record.original_identity[3].isoformat(),
                record.original_identity[4],
            ],
            separators=(",", ":"),
        )
        corrected = record.corrected_bar
        corrected_key = json.dumps(
            [
                corrected.identity[0],
                corrected.identity[1],
                corrected.identity[2],
                corrected.identity[3].isoformat(),
                corrected.identity[4],
            ],
            separators=(",", ":"),
        )
        original = self._connection.execute(
            """
            SELECT 1 FROM signal_lifecycle_daily_observations
            WHERE identity_key = ? AND signal_id = ?
            """,
            (original_key, str(record.signal_id)),
        ).fetchone()
        if original is None:
            raise ValueError("correction references a missing original observation")
        payload = self._serialize_correction(record)
        existing = self._connection.execute(
            "SELECT payload_json FROM signal_lifecycle_daily_bar_corrections WHERE correction_id = ?",
            (str(record.correction_id),),
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != payload:
                raise ValueError("conflicting lifecycle correction replay")
            return
        self._connection.execute(
            """
            INSERT INTO signal_lifecycle_daily_bar_corrections(
                correction_id, signal_id, original_identity_key,
                corrected_identity_key, operator_id, reason, recorded_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(record.correction_id),
                str(record.signal_id),
                original_key,
                corrected_key,
                record.operator_id,
                record.reason,
                record.recorded_at.isoformat(),
                payload,
            ),
        )

    def corrections(self, signal_id: UUID) -> tuple[LifecycleCorrectionRecord, ...]:
        rows = self._connection.execute(
            """
            SELECT payload_json FROM signal_lifecycle_daily_bar_corrections
            WHERE signal_id = ?
            ORDER BY recorded_at ASC, correction_id ASC
            """,
            (str(signal_id),),
        ).fetchall()
        return tuple(
            self._deserialize_correction(str(row[0]))
            for row in rows
        )

    @staticmethod
    def _serialize_correction(record: LifecycleCorrectionRecord) -> str:
        bar = record.corrected_bar
        payload = {
            "correction_id": str(record.correction_id),
            "signal_id": str(record.signal_id),
            "original_identity": [
                record.original_identity[0],
                record.original_identity[1],
                record.original_identity[2],
                record.original_identity[3].isoformat(),
                record.original_identity[4],
            ],
            "operator_id": record.operator_id,
            "reason": record.reason,
            "calendar_version": record.calendar_version,
            "recorded_at": record.recorded_at.isoformat(),
            "status": record.status,
            "corrected_bar": {
                "symbol": bar.symbol,
                "provider": bar.provider,
                "timeframe": bar.timeframe,
                "candle_at": bar.candle_at.isoformat(),
                "observed_at": bar.observed_at.isoformat(),
                "revision": bar.revision,
                "source_reference": bar.source_reference,
                "finality_attestation": bar.finality_attestation,
                "is_final": bar.is_final,
                "open": str(bar.open),
                "high": str(bar.high),
                "low": str(bar.low),
                "close": str(bar.close),
            },
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _deserialize_correction(payload_text: str) -> LifecycleCorrectionRecord:
        payload = json.loads(payload_text)
        item = payload["corrected_bar"]
        bar = CompletedDailyBarObservation(
            symbol=str(item["symbol"]),
            provider=str(item["provider"]),
            timeframe=str(item["timeframe"]),
            candle_at=datetime.fromisoformat(str(item["candle_at"])),
            observed_at=datetime.fromisoformat(str(item["observed_at"])),
            revision=str(item["revision"]),
            source_reference=str(item["source_reference"]),
            finality_attestation=str(item["finality_attestation"]),
            is_final=bool(item["is_final"]),
            open=Decimal(str(item["open"])),
            high=Decimal(str(item["high"])),
            low=Decimal(str(item["low"])),
            close=Decimal(str(item["close"])),
        )
        original = payload["original_identity"]
        return LifecycleCorrectionRecord(
            correction_id=UUID(str(payload["correction_id"])),
            signal_id=UUID(str(payload["signal_id"])),
            original_identity=(
                str(original[0]),
                str(original[1]),
                str(original[2]),
                datetime.fromisoformat(str(original[3])),
                str(original[4]),
            ),
            corrected_bar=bar,
            operator_id=str(payload["operator_id"]),
            reason=str(payload["reason"]),
            calendar_version=str(payload["calendar_version"]),
            recorded_at=datetime.fromisoformat(str(payload["recorded_at"])),
            status=str(payload["status"]),
        )

    def record_observation(self, record: LifecycleObservationRecord) -> None:
        bar = record.bar
        identity_key = json.dumps(
            [*bar.identity[:3], bar.identity[3].isoformat(), bar.identity[4]],
            separators=(",", ":"),
        )
        payload = self._serialize_observation(record)
        existing = self._connection.execute(
            "SELECT payload_json FROM signal_lifecycle_daily_observations WHERE identity_key = ? AND signal_id = ?",
            (identity_key, str(record.signal_id)),
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != payload:
                raise ValueError("conflicting replay for completed daily candle identity")
            return
        self._connection.execute(
            """
            INSERT INTO signal_lifecycle_daily_observations(
                identity_key, signal_id, symbol, candle_at, observed_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                identity_key,
                str(record.signal_id),
                bar.symbol.strip().upper(),
                bar.candle_at.isoformat(),
                bar.observed_at.isoformat(),
                payload,
            ),
        )

    @staticmethod
    def _serialize_observation(record: LifecycleObservationRecord) -> str:
        bar = record.bar
        payload = {
            "signal_id": str(record.signal_id),
            "policy_version": record.policy_version,
            "calendar_version": record.calendar_version,
            "resulting_status": record.resulting_status.value,
            "bar": {
                "symbol": bar.symbol.strip().upper(),
                "provider": bar.provider.strip(),
                "timeframe": bar.timeframe.strip().upper(),
                "candle_at": bar.candle_at.isoformat(),
                "observed_at": bar.observed_at.isoformat(),
                "revision": bar.revision.strip(),
                "source_reference": bar.source_reference,
                "finality_attestation": bar.finality_attestation,
                "is_final": bar.is_final,
                "open": str(bar.open),
                "high": str(bar.high),
                "low": str(bar.low),
                "close": str(bar.close),
            },
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _deserialize_observation(payload_text: str) -> LifecycleObservationRecord:
        payload = json.loads(payload_text)
        item = payload["bar"]
        bar = CompletedDailyBarObservation(
            symbol=str(item["symbol"]),
            provider=str(item["provider"]),
            timeframe=str(item["timeframe"]),
            candle_at=datetime.fromisoformat(str(item["candle_at"])),
            observed_at=datetime.fromisoformat(str(item["observed_at"])),
            revision=str(item["revision"]),
            source_reference=str(item["source_reference"]),
            finality_attestation=str(item["finality_attestation"]),
            is_final=bool(item["is_final"]),
            open=Decimal(str(item["open"])),
            high=Decimal(str(item["high"])),
            low=Decimal(str(item["low"])),
            close=Decimal(str(item["close"])),
        )
        return LifecycleObservationRecord(
            signal_id=UUID(str(payload["signal_id"])),
            bar=bar,
            policy_version=str(payload["policy_version"]),
            calendar_version=str(payload["calendar_version"]),
            resulting_status=SignalStatus(str(payload["resulting_status"])),
        )

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

    def latest_for_identity(
        self,
        symbol: str,
        strategy_id: str,
        strategy_version: str,
        generated_at: datetime,
    ) -> SignalRecord | None:
        rows = self._connection.execute(
            """
            SELECT h.signal_id, h.event, h.recorded_at, h.signal_json
            FROM signal_history h
            JOIN signal_identities i ON i.signal_id = h.signal_id
            WHERE i.symbol = ?
            ORDER BY h.id DESC
            """,
            (symbol.strip().upper(),),
        ).fetchall()
        for row in rows:
            record = self._history._to_record(row)
            if (
                record.signal.strategy_id == strategy_id
                and record.signal.strategy_version == strategy_version
                and record.signal.generated_at == generated_at
            ):
                return record
        return None

    def latest_for_signal(self, signal_id: UUID) -> SignalRecord | None:
        row = self._connection.execute(
            """
            SELECT signal_id, event, recorded_at, signal_json
            FROM signal_history
            WHERE signal_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (str(signal_id),),
        ).fetchone()
        return self._history._to_record(row) if row else None

    def record_signal(
        self, signal: Signal, event: str, recorded_at: datetime, *, signal_id: UUID | None = None
    ) -> SignalRecord:
        if signal_id is not None:
            if not event.strip():
                raise ValueError("event is required")
            self._history._require_aware(recorded_at, "recorded_at")
            payload = self._history._serialize_signal(signal)
            identity = self._connection.execute(
                "SELECT symbol, strategy_id, generated_at FROM signal_identities WHERE signal_id = ?",
                (str(signal_id),),
            ).fetchone()
            if identity is None:
                raise ValueError("signal identity does not exist")
            if (
                str(identity[0]).strip().upper() != signal.symbol.strip().upper()
                or str(identity[1]) != signal.strategy_id
                or datetime.fromisoformat(str(identity[2])) != signal.generated_at
            ):
                raise ValueError("signal update must preserve its immutable identity")
            latest_payload = self._connection.execute(
                """
                SELECT signal_json FROM signal_history
                WHERE signal_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (str(signal_id),),
            ).fetchone()
            if latest_payload is None:
                raise ValueError("signal identity has no history")
            current_signal = self._history._deserialize_signal(str(latest_payload[0]))
            if current_signal.strategy_version != signal.strategy_version:
                raise ValueError("signal update must preserve its immutable identity")
            existing = self._connection.execute(
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
            self._connection.execute(
                """
                INSERT INTO signal_history(signal_id, event, recorded_at, signal_json)
                VALUES (?, ?, ?, ?)
                """,
                (str(signal_id), event.strip(), recorded_at.isoformat(), payload),
            )
            return SignalRecord(signal_id, signal, recorded_at, event.strip())
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
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid4()), *identity),
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
                signal_id=UUID(signal_id),
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
            signal_id=UUID(signal_id),
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
        self._initialize_observation_ledger()

    def _initialize_observation_ledger(self) -> None:
        connection = connect_sqlite(self._database_path)
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_lifecycle_daily_observations (
                    identity_key TEXT NOT NULL,
                    signal_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    candle_at TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY(identity_key, signal_id),
                    FOREIGN KEY(signal_id) REFERENCES signal_identities(signal_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_lifecycle_daily_observations_symbol_date
                ON signal_lifecycle_daily_observations(symbol, candle_at)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_lifecycle_daily_observations_signal_date
                ON signal_lifecycle_daily_observations(signal_id, candle_at)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_lifecycle_daily_bar_corrections (
                    correction_id TEXT PRIMARY KEY,
                    signal_id TEXT NOT NULL,
                    original_identity_key TEXT NOT NULL,
                    corrected_identity_key TEXT NOT NULL,
                    operator_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(signal_id) REFERENCES signal_identities(signal_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_lifecycle_bar_corrections_signal_time
                ON signal_lifecycle_daily_bar_corrections(signal_id, recorded_at)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_lifecycle_session_gap_events (
                    event_id TEXT PRIMARY KEY,
                    gap_id TEXT NOT NULL,
                    signal_id TEXT NOT NULL,
                    session_date TEXT NOT NULL,
                    calendar_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY(signal_id) REFERENCES signal_identities(signal_id),
                    CHECK(status IN ('STALE', 'RESOLVED'))
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_lifecycle_session_gaps_signal_date
                ON signal_lifecycle_session_gap_events(signal_id, session_date, recorded_at)
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_lifecycle_session_gaps_no_update
                BEFORE UPDATE ON signal_lifecycle_session_gap_events
                BEGIN
                    SELECT RAISE(ABORT, 'lifecycle session gaps are append-only');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_lifecycle_session_gaps_no_delete
                BEFORE DELETE ON signal_lifecycle_session_gap_events
                BEGIN
                    SELECT RAISE(ABORT, 'lifecycle session gaps are append-only');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_lifecycle_bar_corrections_no_update
                BEFORE UPDATE ON signal_lifecycle_daily_bar_corrections
                BEGIN
                    SELECT RAISE(ABORT, 'lifecycle corrections are append-only');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_lifecycle_bar_corrections_no_delete
                BEFORE DELETE ON signal_lifecycle_daily_bar_corrections
                BEGIN
                    SELECT RAISE(ABORT, 'lifecycle corrections are append-only');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_lifecycle_daily_observations_no_update
                BEFORE UPDATE ON signal_lifecycle_daily_observations
                BEGIN
                    SELECT RAISE(ABORT, 'lifecycle observations are append-only');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_lifecycle_daily_observations_no_delete
                BEFORE DELETE ON signal_lifecycle_daily_observations
                BEGIN
                    SELECT RAISE(ABORT, 'lifecycle observations are append-only');
                END
                """
            )
            connection.commit()
        finally:
            connection.close()

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
