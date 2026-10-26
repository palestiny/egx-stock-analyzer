from typing import Protocol
from uuid import UUID

from app.domain.opportunity.trading_opportunity import (
    OpportunityStatus,
    TradingOpportunity,
)


class OpportunityStateConflict(RuntimeError):
    """Raised when a lifecycle write is based on a stale opportunity state."""


class TradingOpportunityStore(Protocol):
    def create(self, opportunity: TradingOpportunity) -> None:
        ...

    def get(self, opportunity_id: UUID) -> TradingOpportunity | None:
        ...

    def append_transition(
        self,
        opportunity: TradingOpportunity,
        *,
        expected_status: OpportunityStatus,
    ) -> TradingOpportunity:
        ...

    def list_by_status(
        self,
        statuses: tuple[OpportunityStatus, ...],
        *,
        limit: int = 100,
    ) -> tuple[TradingOpportunity, ...]:
        ...
