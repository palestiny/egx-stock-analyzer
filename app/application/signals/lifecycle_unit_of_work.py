from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Callable, Protocol, TypeVar

from app.application.alerts.ports import AlertPublisher
from app.application.signals.store import SignalHistoryStore, SignalRecord
from app.application.signals.track_record import TrackRecordStore
from app.domain.alerts.model import AlertEvent
from app.domain.signals.model import Signal
from app.domain.signals.outcome import SignalOutcomeRecord

T = TypeVar("T")


class SignalLifecycleTransaction(Protocol):
    def latest(self, symbol: str) -> SignalRecord | None: ...
    def record_signal(
        self, signal: Signal, event: str, recorded_at
    ) -> SignalRecord: ...
    def record_outcome(self, outcome: SignalOutcomeRecord) -> None: ...
    def publish_alert(self, event: AlertEvent) -> None: ...


class SignalLifecycleUnitOfWork(Protocol):
    def execute(self, operation: Callable[[SignalLifecycleTransaction], T]) -> T: ...


class _InMemoryTransaction:
    def __init__(
        self,
        history: SignalHistoryStore,
        alerts: AlertPublisher,
        track_record: TrackRecordStore,
    ) -> None:
        self._history = history
        self._alerts = alerts
        self._track_record = track_record

    def latest(self, symbol: str) -> SignalRecord | None:
        return self._history.latest(symbol)

    def record_signal(self, signal: Signal, event: str, recorded_at):
        return self._history.record(signal, event, recorded_at)

    def record_outcome(self, outcome: SignalOutcomeRecord) -> None:
        self._track_record.record(outcome)

    def publish_alert(self, event: AlertEvent) -> None:
        self._alerts.publish(event)


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

    def execute(self, operation: Callable[[SignalLifecycleTransaction], T]) -> T:
        with self._lock:
            stores = (self._history, self._alerts, self._track_record)
            snapshots = [deepcopy(store.__dict__) for store in stores]
            try:
                return operation(
                    _InMemoryTransaction(
                        self._history, self._alerts, self._track_record
                    )
                )
            except Exception:
                for store, snapshot in zip(stores, snapshots, strict=True):
                    store.__dict__.clear()
                    store.__dict__.update(snapshot)
                raise
