from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.signals.outcome import SignalOutcomeRecord


class TrackRecordStore(Protocol):
    def record(self, outcome: SignalOutcomeRecord) -> None: ...
    def get(self, signal_id: UUID) -> SignalOutcomeRecord | None: ...
    def all(self) -> tuple[SignalOutcomeRecord, ...]: ...


class InMemoryTrackRecordStore:
    def __init__(self) -> None:
        self._records: dict[UUID, SignalOutcomeRecord] = {}

    def record(self, outcome: SignalOutcomeRecord) -> None:
        existing = self._records.get(outcome.signal_id)
        if existing is not None:
            if existing != outcome:
                raise ValueError("different outcome already recorded")
            return
        self._records[outcome.signal_id] = outcome

    def get(self, signal_id: UUID) -> SignalOutcomeRecord | None:
        return self._records.get(signal_id)

    def all(self) -> tuple[SignalOutcomeRecord, ...]:
        return tuple(self._records.values())
