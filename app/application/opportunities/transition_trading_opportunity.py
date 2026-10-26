from datetime import datetime
from uuid import UUID

from app.application.opportunities.opportunity_store import TradingOpportunityStore
from app.domain.opportunity.trading_opportunity import (
    OpportunityStatus,
    TradingOpportunity,
)


class TradingOpportunityNotFound(LookupError):
    """Raised when a requested opportunity does not exist."""


class TransitionTradingOpportunity:
    def __init__(self, store: TradingOpportunityStore) -> None:
        self._store = store

    def execute(
        self,
        opportunity_id: UUID,
        new_status: OpportunityStatus,
        *,
        occurred_at: datetime,
        reason: str,
        actor: str,
        evidence_version: str | None = None,
    ) -> TradingOpportunity:
        current = self._store.get(opportunity_id)
        if current is None:
            raise TradingOpportunityNotFound("Trading opportunity was not found")

        transitioned = current.transition_to(
            new_status,
            occurred_at=occurred_at,
            reason=reason,
            actor=actor,
            evidence_version=evidence_version,
        )
        return self._store.append_transition(
            transitioned,
            expected_status=current.status,
        )
