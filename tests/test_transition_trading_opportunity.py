from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.opportunities.transition_trading_opportunity import (
    TradingOpportunityNotFound,
    TransitionTradingOpportunity,
)
from app.domain.opportunity.trading_opportunity import (
    OpportunityEvidence,
    OpportunityStatus,
    OpportunityTarget,
    TradingOpportunity,
)
from app.infrastructure.persistence.sqlite_trading_opportunity_store import (
    SQLiteTradingOpportunityStore,
)


NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def make_opportunity() -> TradingOpportunity:
    return TradingOpportunity.create(
        symbol="COMI",
        timeframe="1d",
        strategy_version="entry-v1",
        created_at=NOW,
        expires_at=NOW + timedelta(days=5),
        entry_low=Decimal("80"),
        entry_high=Decimal("81"),
        invalidation_price=Decimal("78"),
        targets=(OpportunityTarget(Decimal("85"), "Prior high"),),
        evidence=(
            OpportunityEvidence(
                evidence_type="support_rejection",
                description="Price rejected a documented support area",
                observed_at=NOW,
                source="daily_ohlcv",
                source_version="dataset-v1",
            ),
        ),
    )


def test_transition_use_case_persists_auditable_state_change(tmp_path) -> None:
    store = SQLiteTradingOpportunityStore(tmp_path / "opportunities.db")
    opportunity = make_opportunity()
    store.create(opportunity)
    use_case = TransitionTradingOpportunity(store)

    result = use_case.execute(
        opportunity.opportunity_id,
        OpportunityStatus.WATCHING,
        occurred_at=NOW + timedelta(minutes=1),
        reason="Setup meets watch rules",
        actor="signal-evaluator",
        evidence_version="dataset-v1",
    )

    assert result.status is OpportunityStatus.WATCHING
    assert len(result.lifecycle_events) == 1
    assert result.lifecycle_events[0].actor == "signal-evaluator"
    assert store.get(opportunity.opportunity_id) == result


def test_transition_use_case_rejects_missing_opportunity(tmp_path) -> None:
    use_case = TransitionTradingOpportunity(
        SQLiteTradingOpportunityStore(tmp_path / "opportunities.db")
    )

    with pytest.raises(TradingOpportunityNotFound, match="was not found"):
        use_case.execute(
            uuid4(),
            OpportunityStatus.WATCHING,
            occurred_at=NOW,
            reason="Missing entity",
            actor="test",
        )


def test_transition_use_case_does_not_persist_invalid_transition(tmp_path) -> None:
    store = SQLiteTradingOpportunityStore(tmp_path / "opportunities.db")
    opportunity = make_opportunity()
    store.create(opportunity)
    use_case = TransitionTradingOpportunity(store)

    with pytest.raises(ValueError, match="Transition from draft to active is not allowed"):
        use_case.execute(
            opportunity.opportunity_id,
            OpportunityStatus.ACTIVE,
            occurred_at=NOW + timedelta(minutes=1),
            reason="Invalid state jump",
            actor="test",
        )

    assert store.get(opportunity.opportunity_id) == opportunity
