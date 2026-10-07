from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.domain.signals.model import Signal


@dataclass(frozen=True)
class SignalRecord:
    signal_id: UUID
    signal: Signal
    recorded_at: datetime
    event: str


class SignalHistoryStore(Protocol):
    def record(self, signal: Signal, event: str, recorded_at: datetime) -> SignalRecord: ...
    def get(self, signal_id: UUID) -> SignalRecord | None: ...
    def history(self, signal_id: UUID) -> tuple[SignalRecord, ...]: ...
    def latest(self, symbol: str) -> SignalRecord | None: ...


class InMemorySignalHistoryStore:
    def __init__(self) -> None:
        self._records: dict[UUID, list[SignalRecord]] = {}
        self._by_symbol: dict[str, UUID] = {}
        self._by_identity: dict[tuple[str, str, str, datetime], UUID] = {}

    def record(self, signal: Signal, event: str, recorded_at: datetime) -> SignalRecord:
        if not event.strip():
            raise ValueError("event is required")
        normalized = signal.symbol.strip().upper()
        identity = (normalized, signal.strategy_id, signal.strategy_version, signal.generated_at)
        signal_id = self._by_identity.get(identity)
        if signal_id is None:
            signal_id = uuid4()
            self._by_identity[identity] = signal_id
        self._by_symbol[normalized] = signal_id
        record = SignalRecord(signal_id, signal, recorded_at, event)
        self._records.setdefault(signal_id, []).append(record)
        return record

    def get(self, signal_id: UUID) -> SignalRecord | None:
        records = self._records.get(signal_id, [])
        return records[-1] if records else None

    def history(self, signal_id: UUID) -> tuple[SignalRecord, ...]:
        return tuple(self._records.get(signal_id, ()))

    def latest(self, symbol: str) -> SignalRecord | None:
        signal_id = self._by_symbol.get(symbol.strip().upper())
        return self.get(signal_id) if signal_id else None
