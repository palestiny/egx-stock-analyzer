from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import date, datetime
from threading import RLock
from zoneinfo import ZoneInfo
from typing import Callable, Protocol, TypeVar
from uuid import UUID

from app.application.alerts.ports import AlertPublisher
from app.application.signals.store import SignalHistoryStore, SignalRecord
from app.application.signals.track_record import TrackRecordStore
from app.domain.alerts.model import AlertEvent
from app.domain.signals.model import Signal, SignalStatus
from app.domain.signals.lifecycle import CompletedDailyBarObservation
from app.domain.signals.outcome import SignalOutcomeRecord

T = TypeVar("T")


@dataclass(frozen=True)
class LifecycleSessionGapEvent:
    event_id: UUID
    gap_id: UUID
    signal_id: UUID
    session_date: date
    calendar_version: str
    status: str
    reason: str
    recorded_at: datetime


@dataclass(frozen=True)
class LifecycleCorrectionRecord:
    correction_id: UUID
    signal_id: UUID
    original_identity: tuple[str, str, str, datetime, str]
    corrected_bar: CompletedDailyBarObservation
    operator_id: str
    reason: str
    calendar_version: str
    recorded_at: datetime
    status: str = "RECORDED_NOT_REEVALUATED"


@dataclass(frozen=True)
class LifecycleCorrectionReviewDecision:
    decision_id: UUID
    correction_id: UUID
    signal_id: UUID
    decision: str
    reviewer_id: str
    reason: str
    recorded_at: datetime


@dataclass(frozen=True)
class LifecycleObservationRecord:
    signal_id: UUID
    bar: CompletedDailyBarObservation
    policy_version: str
    calendar_version: str
    resulting_status: SignalStatus


@dataclass(frozen=True)
class LifecycleCorrectionRebuildRecord:
    rebuild_id: UUID
    correction_id: UUID
    signal_id: UUID
    operator_id: str
    previous_status: SignalStatus
    resulting_status: SignalStatus
    observation_count: int
    replay_digest: str
    superseded_event_id: UUID | None
    correction_event_id: UUID | None
    recorded_at: datetime



@dataclass(frozen=True)
class LifecycleBootstrapRecord:
    batch_id: UUID
    signal_id: UUID
    baseline_date: date
    publication_event: str
    publication_recorded_at: datetime
    operator_id: str
    reason: str
    calendar_version: str
    recorded_at: datetime
    idempotency_key: str


@dataclass(frozen=True)
class LifecycleBootstrapBatchRecord:
    batch_id: UUID
    calendar_version: str
    operator_id: str
    reason: str
    recorded_at: datetime
    opportunity_count: int
    batch_digest: str


class SignalLifecycleTransaction(Protocol):
    def latest(self, symbol: str) -> SignalRecord | None: ...
    def latest_for_identity(
        self, symbol: str, strategy_id: str, strategy_version: str, generated_at: datetime
    ) -> SignalRecord | None: ...
    def latest_for_signal(self, signal_id: UUID) -> SignalRecord | None: ...
    def record_signal(
        self, signal: Signal, event: str, recorded_at: datetime, *, signal_id: UUID | None = None
    ) -> SignalRecord: ...
    def record_outcome(self, outcome: SignalOutcomeRecord) -> None: ...
    def publish_alert(self, event: AlertEvent) -> None: ...
    def get_observation(
        self, signal_id: UUID, identity: tuple[str, str, str, datetime, str]
    ) -> LifecycleObservationRecord | None: ...
    def latest_observation(self, signal_id: UUID) -> LifecycleObservationRecord | None: ...
    def observations(self, signal_id: UUID) -> tuple[LifecycleObservationRecord, ...]: ...
    def signal_history(self, signal_id: UUID) -> tuple[SignalRecord, ...]: ...
    def record_observation(self, record: LifecycleObservationRecord) -> None: ...
    def record_correction_rebuild(self, record: LifecycleCorrectionRebuildRecord) -> None: ...
    def correction_rebuilds(self, signal_id: UUID) -> tuple[LifecycleCorrectionRebuildRecord, ...]: ...
    def delivered_recipients(self, event_id: UUID) -> tuple[UUID, ...]: ...
    def supersede_alert(self, event_id: UUID, reason: str, *, now: datetime) -> bool: ...
    def record_correction(self, record: LifecycleCorrectionRecord) -> None: ...
    def corrections(self, signal_id: UUID) -> tuple[LifecycleCorrectionRecord, ...]: ...
    def record_correction_review_decision(self, decision: LifecycleCorrectionReviewDecision) -> None: ...
    def correction_review_decisions(self, signal_id: UUID) -> tuple[LifecycleCorrectionReviewDecision, ...]: ...
    def record_session_gap_event(self, event: LifecycleSessionGapEvent) -> None: ...
    def session_gap_events(self, signal_id: UUID) -> tuple[LifecycleSessionGapEvent, ...]: ...
    def record_bootstrap_batch(self, batch: LifecycleBootstrapBatchRecord, records: tuple[LifecycleBootstrapRecord, ...]) -> None: ...
    def bootstrap_records(self, signal_id: UUID) -> tuple[LifecycleBootstrapRecord, ...]: ...
    def bootstrap_batches(self) -> tuple[LifecycleBootstrapBatchRecord, ...]: ...


class SignalLifecycleUnitOfWork(Protocol):
    def execute(self, operation: Callable[[SignalLifecycleTransaction], T]) -> T: ...


class _InMemoryTransaction:
    def __init__(
        self,
        history: SignalHistoryStore,
        alerts: AlertPublisher,
        track_record: TrackRecordStore,
        observations: dict[tuple[UUID, tuple[str, str, str, datetime, str]], LifecycleObservationRecord],
        corrections: dict[UUID, LifecycleCorrectionRecord],
        correction_decisions: dict[UUID, LifecycleCorrectionReviewDecision],
        gap_events: dict[UUID, LifecycleSessionGapEvent],
        rebuilds: dict[UUID, LifecycleCorrectionRebuildRecord],
        bootstrap_records: dict[str, LifecycleBootstrapRecord],
        bootstrap_batches: dict[UUID, LifecycleBootstrapBatchRecord],
    ) -> None:
        self._history = history
        self._alerts = alerts
        self._track_record = track_record
        self._observations = observations
        self._corrections = corrections
        self._correction_decisions = correction_decisions
        self._gap_events = gap_events

        self._rebuilds = rebuilds
        self._bootstrap_records = bootstrap_records
        self._bootstrap_batches = bootstrap_batches

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
        existing_batch = self._bootstrap_batches.get(batch.batch_id)
        if existing_batch is not None:
            if replace(existing_batch, recorded_at=batch.recorded_at) != batch or any(
                self._bootstrap_records.get(r.idempotency_key) is None
                or replace(self._bootstrap_records[r.idempotency_key], recorded_at=r.recorded_at) != r
                for r in records
            ):
                raise ValueError("conflicting lifecycle bootstrap batch replay")
            return
        if len({r.signal_id for r in records}) != len(records):
            raise ValueError("bootstrap batch contains duplicate opportunity identities")
        for record in records:
            if (record.batch_id != batch.batch_id or record.calendar_version != batch.calendar_version
                or record.operator_id != batch.operator_id or record.reason != batch.reason
                or record.publication_event not in {"PUBLISHED", "PUBLISHED_VERSION"} or not record.idempotency_key.strip()
                or record.publication_recorded_at.tzinfo is None or record.publication_recorded_at.utcoffset() is None
                or record.publication_recorded_at > record.recorded_at
                or record.baseline_date != record.publication_recorded_at.astimezone(ZoneInfo("Africa/Cairo")).date()
                or record.recorded_at.tzinfo is None or record.recorded_at.utcoffset() is None
                or record.recorded_at != batch.recorded_at
                or record.idempotency_key != f"{record.signal_id}:{record.calendar_version}"):
                raise ValueError("invalid lifecycle bootstrap record")
            existing = self._bootstrap_records.get(record.idempotency_key)
            if existing is not None and existing != record:
                raise ValueError("conflicting lifecycle bootstrap record replay")
            if any(r.signal_id == record.signal_id and r.calendar_version == record.calendar_version
                   and r.idempotency_key != record.idempotency_key for r in self._bootstrap_records.values()):
                raise ValueError("opportunity already bootstrapped for this calendar version")
        for record in records:
            self._bootstrap_records[record.idempotency_key] = record
        self._bootstrap_batches[batch.batch_id] = batch

    def bootstrap_records(self, signal_id: UUID) -> tuple[LifecycleBootstrapRecord, ...]:
        return tuple(sorted((r for r in self._bootstrap_records.values() if r.signal_id == signal_id),
                            key=lambda r: (r.recorded_at, r.calendar_version)))

    def bootstrap_batches(self) -> tuple[LifecycleBootstrapBatchRecord, ...]:
        return tuple(sorted(self._bootstrap_batches.values(), key=lambda r: r.recorded_at))

    def latest(self, symbol: str) -> SignalRecord | None:
        return self._history.latest(symbol)

    def latest_for_signal(self, signal_id: UUID) -> SignalRecord | None:
        return self._history.get(signal_id)

    def latest_for_identity(self, symbol, strategy_id, strategy_version, generated_at):
        return self._history.latest_for_identity(
            symbol, strategy_id, strategy_version, generated_at
        )

    def record_signal(self, signal: Signal, event: str, recorded_at, *, signal_id=None):
        if signal_id is not None:
            return self._history.record_for_signal(signal_id, signal, event, recorded_at)
        return self._history.record(signal, event, recorded_at)

    def record_outcome(self, outcome: SignalOutcomeRecord) -> None:
        self._track_record.record(outcome)

    def publish_alert(self, event: AlertEvent) -> None:
        self._alerts.publish(event)

    def get_observation(self, signal_id: UUID, identity):
        return self._observations.get((signal_id, identity))

    def latest_observation(self, signal_id: UUID):
        matches = [
            record for record in self._observations.values()
            if record.signal_id == signal_id
        ]
        return max(
            matches,
            key=lambda record: (record.bar.candle_at, record.bar.observed_at),
            default=None,
        )

    def observations(self, signal_id: UUID):
        return tuple(sorted(
            (record for record in self._observations.values() if record.signal_id == signal_id),
            key=lambda record: (record.bar.candle_at, record.bar.observed_at, record.bar.revision),
        ))

    def signal_history(self, signal_id: UUID):
        return self._history.history(signal_id)

    def record_correction_rebuild(self, record: LifecycleCorrectionRebuildRecord) -> None:
        existing = self._rebuilds.get(record.correction_id)
        if existing is not None:
            if existing != record:
                raise ValueError("conflicting lifecycle correction rebuild replay")
            return
        self._rebuilds[record.correction_id] = record

    def correction_rebuilds(self, signal_id: UUID):
        return tuple(sorted(
            (record for record in self._rebuilds.values() if record.signal_id == signal_id),
            key=lambda record: (record.recorded_at, str(record.rebuild_id)),
        ))

    def delivered_recipients(self, event_id: UUID):
        return ()

    def supersede_alert(self, event_id: UUID, reason: str, *, now: datetime) -> bool:
        return False

    def record_session_gap_event(self, event: LifecycleSessionGapEvent) -> None:
        existing = self._gap_events.get(event.event_id)
        if existing is not None:
            if (
                existing.gap_id != event.gap_id
                or existing.signal_id != event.signal_id
                or existing.session_date != event.session_date
                or existing.calendar_version != event.calendar_version
                or existing.status != event.status
                or existing.reason != event.reason
            ):
                raise ValueError("conflicting lifecycle session-gap event replay")
            return
        self._gap_events[event.event_id] = event

    def session_gap_events(self, signal_id: UUID) -> tuple[LifecycleSessionGapEvent, ...]:
        return tuple(
            sorted(
                (
                    event for event in self._gap_events.values()
                    if event.signal_id == signal_id
                ),
                # Preserve append order for events on the same session date.
                # recorded_at may legitimately tie (e.g. deterministic replay in tests),
                # and UUID ordering is not event chronology.
                key=lambda event: event.session_date,
            )
        )

    def record_correction(self, record: LifecycleCorrectionRecord) -> None:
        if self.get_observation(record.signal_id, record.original_identity) is None:
            raise ValueError("correction references a missing original observation")
        existing = self._corrections.get(record.correction_id)
        if existing is not None:
            if existing != record:
                raise ValueError("conflicting lifecycle correction replay")
            return
        self._corrections[record.correction_id] = record

    def corrections(self, signal_id: UUID) -> tuple[LifecycleCorrectionRecord, ...]:
        return tuple(
            sorted(
                (
                    record for record in self._corrections.values()
                    if record.signal_id == signal_id
                ),
                key=lambda record: (record.recorded_at, str(record.correction_id)),
            )
        )

    def record_correction_review_decision(self, decision: LifecycleCorrectionReviewDecision) -> None:
        if decision.correction_id not in self._corrections:
            raise ValueError("correction review references a missing correction")
        existing = self._correction_decisions.get(decision.decision_id)
        if existing is not None:
            if existing != decision:
                raise ValueError("conflicting lifecycle correction review replay")
            return
        self._correction_decisions[decision.decision_id] = decision

    def correction_review_decisions(self, signal_id: UUID) -> tuple[LifecycleCorrectionReviewDecision, ...]:
        correction_ids = {
            record.correction_id
            for record in self._corrections.values()
            if record.signal_id == signal_id
        }
        return tuple(
            sorted(
                (
                    decision for decision in self._correction_decisions.values()
                    if decision.signal_id == signal_id
                    and decision.correction_id in correction_ids
                ),
                key=lambda decision: (decision.recorded_at, str(decision.decision_id)),
            )
        )

    def record_observation(self, record: LifecycleObservationRecord) -> None:
        identity = (record.signal_id, record.bar.identity)
        existing = self._observations.get(identity)
        if existing is not None:
            if existing != record:
                raise ValueError("conflicting replay for completed daily candle identity")
            return
        self._observations[identity] = record


class InMemorySignalLifecycleUnitOfWork:
    """Atomic in-memory test adapter; restores all participating stores on failure."""

    def __init__(
        self,
        history: SignalHistoryStore,
        alerts: AlertPublisher,
        track_record: TrackRecordStore,
    ) -> None:
        self._history = history
        self._alerts = alerts
        self._track_record = track_record
        self._lock = RLock()
        self._observations: dict[tuple[UUID, tuple[str, str, str, datetime, str]], LifecycleObservationRecord] = {}
        self._corrections: dict[UUID, LifecycleCorrectionRecord] = {}
        self._correction_decisions: dict[UUID, LifecycleCorrectionReviewDecision] = {}
        self._gap_events: dict[UUID, LifecycleSessionGapEvent] = {}
        self._rebuilds: dict[UUID, LifecycleCorrectionRebuildRecord] = {}
        self._bootstrap_records: dict[str, LifecycleBootstrapRecord] = {}
        self._bootstrap_batches: dict[UUID, LifecycleBootstrapBatchRecord] = {}

    def execute(self, operation: Callable[[SignalLifecycleTransaction], T]) -> T:
        with self._lock:
            stores = (self._history, self._alerts, self._track_record)
            snapshots = [deepcopy(store.__dict__) for store in stores]
            observation_snapshot = deepcopy(self._observations)
            correction_snapshot = deepcopy(self._corrections)
            correction_decision_snapshot = deepcopy(self._correction_decisions)
            gap_snapshot = deepcopy(self._gap_events)
            rebuild_snapshot = deepcopy(self._rebuilds)
            bootstrap_records_snapshot = deepcopy(self._bootstrap_records)
            bootstrap_batches_snapshot = deepcopy(self._bootstrap_batches)
            try:
                return operation(
                    _InMemoryTransaction(
                        self._history, self._alerts, self._track_record,
                        self._observations,
                        self._corrections,
                        self._correction_decisions,
                        self._gap_events,
                        self._rebuilds,
                        self._bootstrap_records,
                        self._bootstrap_batches,
                    )
                )
            except Exception:
                for store, snapshot in zip(stores, snapshots, strict=True):
                    store.__dict__.clear()
                    store.__dict__.update(snapshot)
                self._observations = observation_snapshot
                self._corrections = correction_snapshot
                self._correction_decisions = correction_decision_snapshot
                self._gap_events = gap_snapshot
                self._rebuilds = rebuild_snapshot
                self._bootstrap_records = bootstrap_records_snapshot
                self._bootstrap_batches = bootstrap_batches_snapshot
                raise
