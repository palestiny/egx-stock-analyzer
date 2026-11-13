from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from threading import RLock
from typing import Callable, Protocol, TypeVar

from app.application.alerts.ports import AlertPublisher
from app.application.signals.store import SignalHistoryStore, SignalRecord
from app.application.signals.track_record import TrackRecordStore
from app.domain.alerts.model import AlertEvent
from app.domain.signals.model import Signal, SignalStatus
from app.domain.signals.lifecycle import CompletedDailyBarObservation
from app.domain.signals.outcome import SignalOutcomeRecord

T = TypeVar("T")


@dataclass(frozen=True)
class LifecycleObservationRecord:
    signal_id: UUID
    bar: CompletedDailyBarObservation
    policy_version: str
    resulting_status: SignalStatus


class SignalLifecycleTransaction(Protocol):
    def latest(self, symbol: str) -> SignalRecord | None: ...
    def record_signal(
        self, signal: Signal, event: str, recorded_at: datetime
    ) -> SignalRecord: ...
    def record_outcome(self, outcome: SignalOutcomeRecord) -> None: ...
    def publish_alert(self, event: AlertEvent) -> None: ...
    def get_observation(
        self, identity: tuple[str, str, str, datetime, str]
    ) -> LifecycleObservationRecord | None: ...
    def latest_observation(self, symbol: str) -> LifecycleObservationRecord | None: ...
    def record_observation(self, record: LifecycleObservationRecord) -> None: ...


class SignalLifecycleUnitOfWork(Protocol):
    def execute(self, operation: Callable[[SignalLifecycleTransaction], T]) -> T: ...


class _InMemoryTransaction:
    def __init__(
        self,
        history: SignalHistoryStore,
        alerts: AlertPublisher,
        track_record: TrackRecordStore,
        observations: dict[tuple[str, str, str, datetime, str], LifecycleObservationRecord],
    ) -> None:
        self._history = history
        self._alerts = alerts
        self._track_record = track_record
        self._observations = observations

    def latest(self, symbol: str) -> SignalRecord | None:
        return self._history.latest(symbol)

    def record_signal(self, signal: Signal, event: str, recorded_at):
        return self._history.record(signal, event, recorded_at)

    def record_outcome(self, outcome: SignalOutcomeRecord) -> None:
        self._track_record.record(outcome)

    def publish_alert(self, event: AlertEvent) -> None:
        self._alerts.publish(event)

    def get_observation(self, identity):
        return self._observations.get(identity)

    def latest_observation(self, symbol: str):
        matches = [
            record for record in self._observations.values()
            if record.bar.symbol.strip().upper() == symbol.strip().upper()
        ]
        return max(
            matches,
            key=lambda record: (record.bar.candle_at, record.bar.observed_at),
            default=None,
        )

    def record_observation(self, record: LifecycleObservationRecord) -> None:
        identity = record.bar.identity
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
        self._observations: dict[tuple[str, str, str, datetime, str], LifecycleObservationRecord] = {}

    def execute(self, operation: Callable[[SignalLifecycleTransaction], T]) -> T:
        with self._lock:
            stores = (self._history, self._alerts, self._track_record)
            snapshots = [deepcopy(store.__dict__) for store in stores]
            observation_snapshot = deepcopy(self._observations)
            try:
                return operation(
                    _InMemoryTransaction(
                        self._history, self._alerts, self._track_record,
                        self._observations,
                    )
                )
            except Exception:
                for store, snapshot in zip(stores, snapshots, strict=True):
                    store.__dict__.clear()
                    store.__dict__.update(snapshot)
                self._observations = observation_snapshot
                raise
