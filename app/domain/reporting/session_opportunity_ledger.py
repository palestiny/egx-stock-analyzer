from dataclasses import dataclass
from enum import StrEnum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.domain.signals.model import SignalStatus
from app.domain.signals.outcome import SignalOutcome


class OutcomeKnowledgeStatus(StrEnum):
    RECORDED = "RECORDED"
    LEGACY_UNKNOWN = "LEGACY_UNKNOWN"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class SessionOpportunityEntry:
    signal_id: UUID
    symbol: str
    publication_time: datetime
    original_entry_lower: Decimal
    original_entry_upper: Decimal
    original_invalidation: Decimal
    original_targets: tuple[tuple[str, Decimal], ...]
    current_status: SignalStatus
    current_evidence: tuple[str, ...]
    market_proxy_outcome: SignalOutcome | None
    market_proxy_return: Decimal | None
    market_proxy_r: Decimal | None
    outcome_observed_at: datetime | None
    source_data_timestamp: datetime | None = None
    outcome_data_timestamp: datetime | None = None
    outcome_event_id: UUID | None = None
    outcome_recorded_at: datetime | None = None
    outcome_knowledge_status: OutcomeKnowledgeStatus = OutcomeKnowledgeStatus.UNRESOLVED


@dataclass(frozen=True)
class SessionOpportunityLedgerReport:
    session_date: date
    generated_at: datetime
    exchange_timezone: str
    methodology_version: str
    opportunities: tuple[SessionOpportunityEntry, ...]
    unresolved_count: int
    resolved_proxy_count: int

    @property
    def total_count(self) -> int:
        return len(self.opportunities)

    @property
    def status_counts(self) -> tuple[tuple[str, int], ...]:
        return tuple(
            (status.value, sum(1 for item in self.opportunities if item.current_status is status))
            for status in SignalStatus
        )
