from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.domain.signals.model import Signal


@dataclass(frozen=True)
class SignalRevisionLink:
    signal_id: UUID
    parent_signal_id: UUID
    revision_number: int
    reason: str
    recorded_at: datetime


@dataclass(frozen=True)
class SignalRecord:
    signal_id: UUID
    signal: Signal
    recorded_at: datetime
    event: str


@dataclass(frozen=True)
class PublishedOpportunityRevision:
    latest: SignalRecord
    publication: SignalRecord


class SignalHistoryStore(Protocol):
    def record(self, signal: Signal, event: str, recorded_at: datetime) -> SignalRecord: ...
    def record_for_signal(
        self, signal_id: UUID, signal: Signal, event: str, recorded_at: datetime
    ) -> SignalRecord: ...
    def record_revision(
        self,
        signal: Signal,
        event: str,
        recorded_at: datetime,
        *,
        parent_signal_id: UUID,
        reason: str,
    ) -> SignalRecord: ...
    def revision_link(self, signal_id: UUID) -> SignalRevisionLink | None: ...
    def get(self, signal_id: UUID) -> SignalRecord | None: ...
    def history(self, signal_id: UUID) -> tuple[SignalRecord, ...]: ...
    def latest(self, symbol: str) -> SignalRecord | None: ...
    def latest_for_identity(
        self, symbol: str, strategy_id: str, strategy_version: str, generated_at: datetime
    ) -> SignalRecord | None: ...
    def all_records(self) -> tuple[SignalRecord, ...]: ...
    def latest_active_published_opportunities(self) -> tuple[PublishedOpportunityRevision, ...]: ...


class InMemorySignalHistoryStore:
    def __init__(self) -> None:
        self._records: dict[UUID, list[SignalRecord]] = {}
        self._by_symbol: dict[str, UUID] = {}
        self._by_identity: dict[tuple[str, str, str, datetime], UUID] = {}
        self._revision_links: dict[UUID, SignalRevisionLink] = {}

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

    def record_for_signal(
        self, signal_id: UUID, signal: Signal, event: str, recorded_at: datetime
    ) -> SignalRecord:
        current = self.get(signal_id)
        if current is None:
            raise ValueError("signal identity does not exist")
        if (
            current.signal.symbol.strip().upper() != signal.symbol.strip().upper()
            or current.signal.strategy_id != signal.strategy_id
            or current.signal.strategy_version != signal.strategy_version
            or current.signal.generated_at != signal.generated_at
        ):
            raise ValueError("signal update must preserve its immutable identity")
        if not event.strip():
            raise ValueError("event is required")
        existing = next(
            (
                item for item in self._records.get(signal_id, ())
                if item.event == event.strip() and item.recorded_at == recorded_at
            ),
            None,
        )
        if existing is not None:
            if existing.signal != signal:
                raise ValueError("different signal event already recorded")
            return existing
        record = SignalRecord(signal_id, signal, recorded_at, event.strip())
        self._records.setdefault(signal_id, []).append(record)
        self._by_symbol[signal.symbol.strip().upper()] = signal_id
        self._by_identity[(signal.symbol.strip().upper(), signal.strategy_id, signal.strategy_version, signal.generated_at)] = signal_id
        return record

    def record_revision(
        self,
        signal: Signal,
        event: str,
        recorded_at: datetime,
        *,
        parent_signal_id: UUID,
        reason: str,
    ) -> SignalRecord:
        if not event.strip():
            raise ValueError("event is required")
        parent = self.get(parent_signal_id)
        if parent is None:
            raise ValueError("parent signal identity does not exist")
        if parent.signal.status.value != "ACTIVE":
            raise ValueError("terminal opportunities cannot be revised")
        latest = self.latest_for_identity(
            parent.signal.symbol,
            parent.signal.strategy_id,
            parent.signal.strategy_version,
            parent.signal.generated_at,
        )
        if latest is None or latest.signal_id != parent_signal_id:
            raise ValueError("revision parent must be the latest opportunity revision")
        if (
            parent.signal.symbol.strip().upper() != signal.symbol.strip().upper()
            or parent.signal.strategy_id != signal.strategy_id
            or parent.signal.strategy_version != signal.strategy_version
            or parent.signal.generated_at != signal.generated_at
        ):
            raise ValueError("revision must preserve the parent opportunity identity")
        if not reason.strip():
            raise ValueError("revision reason is required")
        parent_link = self._revision_links.get(parent_signal_id)
        revision_number = (parent_link.revision_number if parent_link else 1) + 1
        signal_id = uuid4()
        self._revision_links[signal_id] = SignalRevisionLink(
            signal_id, parent_signal_id, revision_number, reason.strip(), recorded_at
        )
        record = SignalRecord(signal_id, signal, recorded_at, event.strip())
        self._records[signal_id] = [record]
        self._by_symbol[signal.symbol.strip().upper()] = signal_id
        self._by_identity[(signal.symbol.strip().upper(), signal.strategy_id, signal.strategy_version, signal.generated_at)] = signal_id
        return record

    def revision_link(self, signal_id: UUID) -> SignalRevisionLink | None:
        return self._revision_links.get(signal_id)

    def get(self, signal_id: UUID) -> SignalRecord | None:
        records = self._records.get(signal_id, [])
        return records[-1] if records else None

    def history(self, signal_id: UUID) -> tuple[SignalRecord, ...]:
        return tuple(self._records.get(signal_id, ()))

    def latest(self, symbol: str) -> SignalRecord | None:
        signal_id = self._by_symbol.get(symbol.strip().upper())
        return self.get(signal_id) if signal_id else None

    def latest_for_identity(
        self,
        symbol: str,
        strategy_id: str,
        strategy_version: str,
        generated_at: datetime,
    ) -> SignalRecord | None:
        normalized_symbol = symbol.strip().upper()
        candidates = [
            records[-1]
            for records in self._records.values()
            if records
            and records[-1].signal.symbol.strip().upper() == normalized_symbol
            and records[-1].signal.strategy_id == strategy_id
            and records[-1].signal.strategy_version == strategy_version
        ]
        return max(
            candidates,
            key=lambda record: (record.recorded_at, str(record.signal_id)),
            default=None,
        )

    def all_records(self) -> tuple[SignalRecord, ...]:
        records = [
            record
            for history in self._records.values()
            for record in history
        ]
        return tuple(sorted(records, key=lambda record: (record.recorded_at, str(record.signal_id))))

    def latest_active_published_opportunities(self) -> tuple[PublishedOpportunityRevision, ...]:
        signal_ids = {record.signal_id for record in self.all_records()}
        superseded_ids = {
            link.parent_signal_id
            for signal_id in signal_ids
            if (link := self.revision_link(signal_id)) is not None
        }
        candidates: list[PublishedOpportunityRevision] = []
        for signal_id in sorted(signal_ids - superseded_ids, key=str):
            latest = self.get(signal_id)
            if latest is None or latest.signal.status.value != "ACTIVE":
                continue
            publication = next(
                (item for item in self.history(signal_id) if item.event in {"PUBLISHED", "PUBLISHED_VERSION"}),
                None,
            )
            if publication is not None:
                candidates.append(PublishedOpportunityRevision(latest=latest, publication=publication))
        return tuple(candidates)
