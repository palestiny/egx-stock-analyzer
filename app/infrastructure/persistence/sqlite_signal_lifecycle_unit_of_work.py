from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable, TypeVar
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.application.signals.lifecycle_unit_of_work import (
    LifecycleBootstrapBatchRecord,
    LifecycleBootstrapRecord,
    LifecycleCorrectionRecord,
    LifecycleCorrectionReviewDecision,
    LifecycleCorrectionRebuildRecord,
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


    def record_bootstrap_batch(self, batch: LifecycleBootstrapBatchRecord, records: tuple[LifecycleBootstrapRecord, ...]) -> None:
        if batch.opportunity_count != len(records) or not records:
            raise ValueError("bootstrap batch record count mismatch")
        if (
            not batch.operator_id.strip()
            or not batch.reason.strip()
            or not batch.calendar_version.strip()
            or len(batch.batch_digest) != 64
            or any(character not in "0123456789abcdef" for character in batch.batch_digest.lower())
        ):
            raise ValueError("bootstrap batch audit fields are required")
        if batch.recorded_at.tzinfo is None or batch.recorded_at.utcoffset() is None:
            raise ValueError("bootstrap batch timestamp must be timezone-aware")
        existing_batch = self._connection.execute(
            """SELECT calendar_version, operator_id, reason, recorded_at, opportunity_count, batch_digest
               FROM signal_lifecycle_bootstrap_batches WHERE batch_id = ?""",
            (str(batch.batch_id),),
        ).fetchone()
        expected_batch = (
            batch.calendar_version, batch.operator_id, batch.reason,
            batch.opportunity_count, batch.batch_digest,
        )
        if existing_batch is not None:
            existing_identity = (
                str(existing_batch[0]), str(existing_batch[1]), str(existing_batch[2]),
                int(existing_batch[4]), str(existing_batch[5]),
            )
            if existing_identity != expected_batch:
                raise ValueError("conflicting lifecycle bootstrap batch replay")
            for record in records:
                existing = self._connection.execute(
                    """SELECT payload_json FROM signal_lifecycle_bootstrap_records
                       WHERE idempotency_key = ?""", (record.idempotency_key,)
                ).fetchone()
                if existing is None:
                    raise ValueError("conflicting lifecycle bootstrap record replay")
                stored_record = self._deserialize_bootstrap_record(str(existing[0]))
                if replace(stored_record, recorded_at=record.recorded_at) != record:
                    raise ValueError("conflicting lifecycle bootstrap record replay")
            return
        if len({record.signal_id for record in records}) != len(records):
            raise ValueError("bootstrap batch contains duplicate opportunity identities")
        payloads = []
        for record in records:
            if (
                record.batch_id != batch.batch_id
                or record.calendar_version != batch.calendar_version
                or record.operator_id != batch.operator_id
                or record.reason != batch.reason
                or record.publication_event not in {"PUBLISHED", "PUBLISHED_VERSION"}
                or not record.idempotency_key.strip()
                or record.publication_recorded_at.tzinfo is None
                or record.publication_recorded_at.utcoffset() is None
                or record.publication_recorded_at > record.recorded_at
                or record.baseline_date != record.publication_recorded_at.astimezone(ZoneInfo("Africa/Cairo")).date()
                or record.recorded_at.tzinfo is None
                or record.recorded_at.utcoffset() is None
                or record.recorded_at != batch.recorded_at
                or record.idempotency_key != f"{record.signal_id}:{record.calendar_version}"
            ):
                raise ValueError("invalid lifecycle bootstrap record")
            payload = self._serialize_bootstrap_record(record)
            existing = self._connection.execute(
                "SELECT payload_json FROM signal_lifecycle_bootstrap_records WHERE idempotency_key = ?",
                (record.idempotency_key,),
            ).fetchone()
            if existing is not None and str(existing[0]) != payload:
                raise ValueError("conflicting lifecycle bootstrap record replay")
            conflict = self._connection.execute(
                """SELECT 1 FROM signal_lifecycle_bootstrap_records
                   WHERE signal_id = ? AND calendar_version = ? AND idempotency_key != ?""",
                (str(record.signal_id), record.calendar_version, record.idempotency_key),
            ).fetchone()
            if conflict is not None:
                raise ValueError("opportunity already bootstrapped for this calendar version")
            payloads.append((record, payload))
        self._connection.execute(
            """INSERT INTO signal_lifecycle_bootstrap_batches(
                batch_id, calendar_version, operator_id, reason, recorded_at, opportunity_count, batch_digest
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (str(batch.batch_id), batch.calendar_version, batch.operator_id, batch.reason,
             batch.recorded_at.isoformat(), batch.opportunity_count, batch.batch_digest),
        )
        for record, payload in payloads:
            self._connection.execute(
                """INSERT OR IGNORE INTO signal_lifecycle_bootstrap_records(
                    idempotency_key, batch_id, signal_id, baseline_date, publication_event,
                    publication_recorded_at, operator_id, reason, calendar_version, recorded_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (record.idempotency_key, str(record.batch_id), str(record.signal_id),
                 record.baseline_date.isoformat(), record.publication_event,
                 record.publication_recorded_at.isoformat(), record.operator_id, record.reason,
                 record.calendar_version, record.recorded_at.isoformat(), payload),
            )

    @staticmethod
    def _serialize_bootstrap_record(record: LifecycleBootstrapRecord) -> str:
        return json.dumps({
            "batch_id": str(record.batch_id),
            "signal_id": str(record.signal_id),
            "baseline_date": record.baseline_date.isoformat(),
            "publication_event": record.publication_event,
            "publication_recorded_at": record.publication_recorded_at.isoformat(),
            "operator_id": record.operator_id,
            "reason": record.reason,
            "calendar_version": record.calendar_version,
            "recorded_at": record.recorded_at.isoformat(),
            "idempotency_key": record.idempotency_key,
        }, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _deserialize_bootstrap_record(payload_text: str) -> LifecycleBootstrapRecord:
        payload = json.loads(payload_text)
        return LifecycleBootstrapRecord(
            batch_id=UUID(str(payload["batch_id"])),
            signal_id=UUID(str(payload["signal_id"])),
            baseline_date=date.fromisoformat(str(payload["baseline_date"])),
            publication_event=str(payload["publication_event"]),
            publication_recorded_at=datetime.fromisoformat(str(payload["publication_recorded_at"])),
            operator_id=str(payload["operator_id"]),
            reason=str(payload["reason"]),
            calendar_version=str(payload["calendar_version"]),
            recorded_at=datetime.fromisoformat(str(payload["recorded_at"])),
            idempotency_key=str(payload["idempotency_key"]),
        )

    def bootstrap_records(self, signal_id: UUID) -> tuple[LifecycleBootstrapRecord, ...]:
        rows = self._connection.execute(
            """SELECT payload_json FROM signal_lifecycle_bootstrap_records
               WHERE signal_id = ? ORDER BY recorded_at ASC, calendar_version ASC""",
            (str(signal_id),),
        ).fetchall()
        return tuple(self._deserialize_bootstrap_record(str(row[0])) for row in rows)

    def bootstrap_batches(self) -> tuple[LifecycleBootstrapBatchRecord, ...]:
        rows = self._connection.execute(
            """SELECT batch_id, calendar_version, operator_id, reason, recorded_at,
                      opportunity_count, batch_digest
               FROM signal_lifecycle_bootstrap_batches ORDER BY recorded_at ASC, batch_id ASC"""
        ).fetchall()
        return tuple(LifecycleBootstrapBatchRecord(
            batch_id=UUID(str(row[0])), calendar_version=str(row[1]), operator_id=str(row[2]),
            reason=str(row[3]), recorded_at=datetime.fromisoformat(str(row[4])),
            opportunity_count=int(row[5]), batch_digest=str(row[6]),
        ) for row in rows)

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

    def observations(self, signal_id: UUID):
        rows = self._connection.execute(
            """SELECT payload_json FROM signal_lifecycle_daily_observations
               WHERE signal_id = ? ORDER BY candle_at ASC, observed_at ASC""",
            (str(signal_id),),
        ).fetchall()
        return tuple(self._deserialize_observation(str(row[0])) for row in rows)

    def signal_history(self, signal_id: UUID) -> tuple[SignalRecord, ...]:
        rows = self._connection.execute(
            """
            SELECT signal_id, event, recorded_at, signal_json
            FROM signal_history
            WHERE signal_id = ?
            ORDER BY id ASC
            """,
            (str(signal_id),),
        ).fetchall()
        return tuple(self._history._to_record(row) for row in rows)

    def record_correction_rebuild(self, record: LifecycleCorrectionRebuildRecord) -> None:
        payload = (
            str(record.rebuild_id), str(record.correction_id), str(record.signal_id), record.operator_id,
            record.previous_status.value, record.resulting_status.value,
            record.observation_count, record.replay_digest,
            str(record.superseded_event_id) if record.superseded_event_id else None,
            str(record.correction_event_id) if record.correction_event_id else None,
            record.recorded_at.isoformat(),
        )
        existing = self._connection.execute(
            """SELECT rebuild_id, correction_id, signal_id, operator_id, previous_status, resulting_status,
                      observation_count, replay_digest, superseded_event_id, correction_event_id, recorded_at
               FROM signal_lifecycle_correction_rebuilds WHERE correction_id = ?""",
            (str(record.correction_id),),
        ).fetchone()
        if existing is not None:
            if tuple(existing) != payload:
                raise ValueError("conflicting lifecycle correction rebuild replay")
            return
        self._connection.execute(
            """INSERT INTO signal_lifecycle_correction_rebuilds(
                rebuild_id, correction_id, signal_id, operator_id, previous_status, resulting_status,
                observation_count, replay_digest, superseded_event_id, correction_event_id, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            payload,
        )

    def correction_rebuilds(self, signal_id: UUID):
        rows = self._connection.execute(
            """SELECT rebuild_id, correction_id, signal_id, operator_id, previous_status, resulting_status,
                      observation_count, replay_digest, superseded_event_id, correction_event_id, recorded_at
               FROM signal_lifecycle_correction_rebuilds WHERE signal_id = ?
               ORDER BY recorded_at ASC, rebuild_id ASC""",
            (str(signal_id),),
        ).fetchall()
        return tuple(LifecycleCorrectionRebuildRecord(
            rebuild_id=UUID(str(row[0])), correction_id=UUID(str(row[1])), signal_id=UUID(str(row[2])),
            operator_id=str(row[3]), previous_status=SignalStatus(str(row[4])), resulting_status=SignalStatus(str(row[5])),
            observation_count=int(row[6]), replay_digest=str(row[7]),
            superseded_event_id=UUID(str(row[8])) if row[8] else None,
            correction_event_id=UUID(str(row[9])) if row[9] else None,
            recorded_at=datetime.fromisoformat(str(row[10])),
        ) for row in rows)

    def delivered_recipients(self, event_id: UUID):
        try:
            rows = self._connection.execute(
                """SELECT user_id FROM signal_alert_deliveries
                   WHERE event_id = ? AND channel = 'telegram' AND status = 'DELIVERED'
                   ORDER BY user_id""",
                (str(event_id),),
            ).fetchall()
        except sqlite3.OperationalError:
            return ()
        return tuple(UUID(str(row[0])) for row in rows)

    def supersede_alert(self, event_id: UUID, reason: str, *, now: datetime) -> bool:
        if not reason.strip():
            raise ValueError("supersede reason is required")
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("supersede timestamp must be timezone-aware")
        try:
            sending = self._connection.execute(
                "SELECT 1 FROM signal_alert_deliveries WHERE event_id = ? AND status = 'SENDING' LIMIT 1",
                (str(event_id),),
            ).fetchone()
            if sending is not None:
                raise ValueError("correction replay must wait for an in-flight original alert delivery")
            self._connection.execute(
                """UPDATE signal_alert_deliveries
                   SET status = 'SUPERSEDED', updated_at = ?, last_error = ?,
                       claim_token = NULL, lease_until = NULL, next_attempt_at = NULL
                   WHERE event_id = ? AND status IN ('PENDING', 'FAILED', 'CLAIMED')""",
                (now.isoformat(), reason.strip(), str(event_id)),
            )
        except sqlite3.OperationalError:
            pass
        cursor = self._connection.execute(
            """UPDATE signal_alert_outbox SET status = 'SUPERSEDED', last_error = ?, delivered_at = NULL
               WHERE event_id = ? AND status IN ('PENDING', 'FAILED')""",
            (reason.strip(), str(event_id)),
        )
        return cursor.rowcount == 1

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
            ORDER BY session_date ASC, rowid ASC
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

    def record_correction_review_decision(self, decision: LifecycleCorrectionReviewDecision) -> None:
        correction = self._connection.execute(
            """
            SELECT 1 FROM signal_lifecycle_daily_bar_corrections
            WHERE correction_id = ? AND signal_id = ?
            """,
            (str(decision.correction_id), str(decision.signal_id)),
        ).fetchone()
        if correction is None:
            raise ValueError("correction review references a missing correction")
        existing = self._connection.execute(
            """
            SELECT correction_id, signal_id, decision, reviewer_id, reason, recorded_at
            FROM signal_lifecycle_correction_review_decisions
            WHERE decision_id = ?
            """,
            (str(decision.decision_id),),
        ).fetchone()
        expected = (
            str(decision.correction_id),
            str(decision.signal_id),
            decision.decision,
            decision.reviewer_id,
            decision.reason,
            decision.recorded_at.isoformat(),
        )
        if existing is not None:
            if tuple(str(value) for value in existing) != expected:
                raise ValueError("conflicting lifecycle correction review replay")
            return
        self._connection.execute(
            """
            INSERT INTO signal_lifecycle_correction_review_decisions(
                decision_id, correction_id, signal_id, decision,
                reviewer_id, reason, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(decision.decision_id),
                str(decision.correction_id),
                str(decision.signal_id),
                decision.decision,
                decision.reviewer_id,
                decision.reason,
                decision.recorded_at.isoformat(),
            ),
        )

    def correction_review_decisions(self, signal_id: UUID) -> tuple[LifecycleCorrectionReviewDecision, ...]:
        rows = self._connection.execute(
            """
            SELECT decision_id, correction_id, signal_id, decision,
                   reviewer_id, reason, recorded_at
            FROM signal_lifecycle_correction_review_decisions
            WHERE signal_id = ?
            ORDER BY recorded_at ASC, decision_id ASC
            """,
            (str(signal_id),),
        ).fetchall()
        return tuple(
            LifecycleCorrectionReviewDecision(
                decision_id=UUID(str(row[0])),
                correction_id=UUID(str(row[1])),
                signal_id=UUID(str(row[2])),
                decision=str(row[3]),
                reviewer_id=str(row[4]),
                reason=str(row[5]),
                recorded_at=datetime.fromisoformat(str(row[6])),
            )
            for row in rows
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
        resolved_signal_id = str(row[0])
        existing = self._connection.execute(
            """
            SELECT signal_json FROM signal_history
            WHERE signal_id = ? AND event = ? AND recorded_at = ?
            """,
            (resolved_signal_id, event.strip(), recorded_at.isoformat()),
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != payload:
                raise ValueError("different signal event already recorded")
            return SignalRecord(
                signal_id=UUID(resolved_signal_id),
                signal=signal,
                recorded_at=recorded_at,
                event=event.strip(),
            )
        self._connection.execute(
            """
            INSERT INTO signal_history(signal_id, event, recorded_at, signal_json)
            VALUES (?, ?, ?, ?)
            """,
            (resolved_signal_id, event.strip(), recorded_at.isoformat(), payload),
        )
        return SignalRecord(
            signal_id=UUID(resolved_signal_id),
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
                CREATE TABLE IF NOT EXISTS signal_lifecycle_bootstrap_batches (
                    batch_id TEXT PRIMARY KEY,
                    calendar_version TEXT NOT NULL,
                    operator_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    opportunity_count INTEGER NOT NULL CHECK(opportunity_count > 0),
                    batch_digest TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_lifecycle_bootstrap_records (
                    idempotency_key TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    signal_id TEXT NOT NULL,
                    baseline_date TEXT NOT NULL,
                    publication_event TEXT NOT NULL,
                    publication_recorded_at TEXT NOT NULL,
                    operator_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    calendar_version TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(batch_id) REFERENCES signal_lifecycle_bootstrap_batches(batch_id),
                    FOREIGN KEY(signal_id) REFERENCES signal_identities(signal_id),
                    UNIQUE(signal_id, calendar_version)
                )
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_lifecycle_bootstrap_batches_no_update
                BEFORE UPDATE ON signal_lifecycle_bootstrap_batches
                BEGIN SELECT RAISE(ABORT, 'lifecycle bootstrap batches are append-only'); END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_lifecycle_bootstrap_batches_no_delete
                BEFORE DELETE ON signal_lifecycle_bootstrap_batches
                BEGIN SELECT RAISE(ABORT, 'lifecycle bootstrap batches are append-only'); END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_lifecycle_bootstrap_records_no_update
                BEFORE UPDATE ON signal_lifecycle_bootstrap_records
                BEGIN SELECT RAISE(ABORT, 'lifecycle bootstrap records are append-only'); END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_lifecycle_bootstrap_records_no_delete
                BEFORE DELETE ON signal_lifecycle_bootstrap_records
                BEGIN SELECT RAISE(ABORT, 'lifecycle bootstrap records are append-only'); END
                """
            )
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
                CREATE TABLE IF NOT EXISTS signal_lifecycle_correction_review_decisions (
                    decision_id TEXT PRIMARY KEY,
                    correction_id TEXT NOT NULL,
                    signal_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY(correction_id) REFERENCES signal_lifecycle_daily_bar_corrections(correction_id),
                    FOREIGN KEY(signal_id) REFERENCES signal_identities(signal_id),
                    CHECK(decision IN ('REJECTED', 'ACCEPTED_NO_STATE_CHANGE', 'REPLAY_REQUIRED'))
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_lifecycle_correction_reviews_signal_time
                ON signal_lifecycle_correction_review_decisions(signal_id, recorded_at, decision_id)
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_lifecycle_correction_reviews_no_update
                BEFORE UPDATE ON signal_lifecycle_correction_review_decisions
                BEGIN
                    SELECT RAISE(ABORT, 'lifecycle correction reviews are append-only');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_lifecycle_correction_reviews_no_delete
                BEFORE DELETE ON signal_lifecycle_correction_review_decisions
                BEGIN
                    SELECT RAISE(ABORT, 'lifecycle correction reviews are append-only');
                END
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_lifecycle_correction_rebuilds (
                    rebuild_id TEXT PRIMARY KEY,
                    correction_id TEXT NOT NULL UNIQUE,
                    signal_id TEXT NOT NULL,
                    operator_id TEXT NOT NULL,
                    previous_status TEXT NOT NULL,
                    resulting_status TEXT NOT NULL,
                    observation_count INTEGER NOT NULL,
                    replay_digest TEXT NOT NULL,
                    superseded_event_id TEXT NULL,
                    correction_event_id TEXT NULL,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY(correction_id) REFERENCES signal_lifecycle_daily_bar_corrections(correction_id),
                    FOREIGN KEY(signal_id) REFERENCES signal_identities(signal_id),
                    CHECK(observation_count >= 1)
                )
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_lifecycle_correction_rebuilds_no_update
                BEFORE UPDATE ON signal_lifecycle_correction_rebuilds
                BEGIN SELECT RAISE(ABORT, 'lifecycle correction rebuilds are append-only'); END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_lifecycle_correction_rebuilds_no_delete
                BEFORE DELETE ON signal_lifecycle_correction_rebuilds
                BEGIN SELECT RAISE(ABORT, 'lifecycle correction rebuilds are append-only'); END
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

    def execute_in_transaction(
        self,
        connection: sqlite3.Connection,
        operation: Callable[[SignalLifecycleTransaction], T],
    ) -> T:
        """Run lifecycle reads/writes on a caller-owned SQLite transaction.

        The caller owns BEGIN/COMMIT/ROLLBACK. This is used by the calendar
        activation coordinator to share one write transaction with the active
        calendar pointer and its append-only activation audit event.
        """
        if not connection.in_transaction:
            raise RuntimeError("a caller-owned SQLite transaction is required")
        connection.execute("PRAGMA foreign_keys = ON")
        transaction = _SQLiteSignalLifecycleTransaction(
            connection,
            self._history,
            self._track_record,
            self._outbox,
        )
        return operation(transaction)

    def execute(self, operation: Callable[[SignalLifecycleTransaction], T]) -> T:
        connection = connect_sqlite(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            connection.execute("BEGIN IMMEDIATE")
            result = self.execute_in_transaction(connection, operation)
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
