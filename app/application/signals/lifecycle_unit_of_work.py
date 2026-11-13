from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from threading import RLock
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
    def record_observation(self, record: LifecycleObservationRecord) -> None: ...
    def record_correction(self, record: LifecycleCorrectionRecord) -> None: ...
    def corrections(self, signal_id: UUID) -> tuple[LifecycleCorrectionRecord, ...]: ...
    def record_correction_review_decision(self, decision: LifecycleCorrectionReviewDecision) -> None: ...
    def correction_review_decisions(self, signal_id: UUID) -> tuple[LifecycleCorrectionReviewDecision, ...]: ...
    def record_session_gap_event(self, event: LifecycleSessionGapEvent) -> None: ...
    def session_gap_events(self, signal_id: UUID) -> tuple[LifecycleSessionGapEvent, ...]: ...


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
    ) -> None:
        self._history = history
        self._alerts = alerts
        self._track_record = track_record
        self._observations = observations
        self._corrections = corrections
        self._correction_decisions = correction_decisions
        self._gap_events = gap_events

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
                key=lambda event: (event.session_date, event.recorded_at, str(event.event_id)),
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

    def execute(self, operation: Callable[[SignalLifecycleTransaction], T]) -> T:
        with self._lock:
            stores = (self._history, self._alerts, self._track_record)
            snapshots = [deepcopy(store.__dict__) for store in stores]
            observation_snapshot = deepcopy(self._observations)
            correction_snapshot = deepcopy(self._corrections)
            correction_decision_snapshot = deepcopy(self._correction_decisions)
            gap_snapshot = deepcopy(self._gap_events)
            try:
                return operation(
                    _InMemoryTransaction(
                        self._history, self._alerts, self._track_record,
                        self._observations,
                        self._corrections,
                        self._correction_decisions,
                        self._gap_events,
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
                raise
