from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.application.opportunities.opportunity_store import OpportunityStateConflict
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
        symbol="EGAL",
        timeframe="1d",
        strategy_version="entry-v1",
        created_at=NOW,
        expires_at=NOW + timedelta(days=7),
        entry_low=Decimal("35.25"),
        entry_high=Decimal("36.00"),
        invalidation_price=Decimal("34.50"),
        targets=(
            OpportunityTarget(Decimal("38.00"), "Prior swing high"),
            OpportunityTarget(Decimal("40.00"), "Measured move"),
        ),
        evidence=(
            OpportunityEvidence(
                evidence_type="breakout_retest",
                description="Daily close reclaimed prior resistance",
                observed_at=NOW,
                source="daily_ohlcv",
                source_version="dataset-v1",
            ),
        ),
    )


def test_store_round_trips_decimal_evidence_and_strategy_version(tmp_path) -> None:
    database = tmp_path / "opportunities.db"
    store = SQLiteTradingOpportunityStore(database)
    opportunity = make_opportunity()

    store.create(opportunity)
    loaded = SQLiteTradingOpportunityStore(database).get(opportunity.opportunity_id)

    assert loaded == opportunity
    assert loaded is not None
    assert loaded.strategy_version == "entry-v1"
    assert loaded.entry_low == Decimal("35.25")
    assert loaded.targets[0].price == Decimal("38.00")
    assert loaded.evidence[0].source_version == "dataset-v1"


def test_transition_and_lifecycle_event_survive_store_reopen(tmp_path) -> None:
    database = tmp_path / "opportunities.db"
    store = SQLiteTradingOpportunityStore(database)
    opportunity = make_opportunity()
    store.create(opportunity)

    transitioned = opportunity.transition_to(
        OpportunityStatus.WATCHING,
        occurred_at=NOW + timedelta(minutes=1),
        reason="Setup passed watch rules",
        actor="signal-evaluator",
        evidence_version="dataset-v1",
    )
    saved = store.append_transition(transitioned, expected_status=OpportunityStatus.DRAFT)
    reloaded = SQLiteTradingOpportunityStore(database).get(opportunity.opportunity_id)

    assert saved == transitioned
    assert reloaded == transitioned
    assert reloaded is not None
    assert len(reloaded.lifecycle_events) == 1
    assert reloaded.lifecycle_events[0].reason == "Setup passed watch rules"


def test_replaying_same_transition_event_is_idempotent(tmp_path) -> None:
    store = SQLiteTradingOpportunityStore(tmp_path / "opportunities.db")
    opportunity = make_opportunity()
    store.create(opportunity)
    transitioned = opportunity.transition_to(
        OpportunityStatus.WATCHING,
        occurred_at=NOW + timedelta(minutes=1),
        reason="Setup passed watch rules",
        actor="signal-evaluator",
    )

    first = store.append_transition(transitioned, expected_status=OpportunityStatus.DRAFT)
    replay = store.append_transition(transitioned, expected_status=OpportunityStatus.DRAFT)

    assert first == replay
    assert len(replay.lifecycle_events) == 1


def test_stale_transition_cannot_overwrite_newer_state(tmp_path) -> None:
    store = SQLiteTradingOpportunityStore(tmp_path / "opportunities.db")
    opportunity = make_opportunity()
    store.create(opportunity)
    watching = opportunity.transition_to(
        OpportunityStatus.WATCHING,
        occurred_at=NOW + timedelta(minutes=1),
        reason="Setup passed watch rules",
        actor="signal-evaluator",
    )
    store.append_transition(watching, expected_status=OpportunityStatus.DRAFT)

    active = watching.transition_to(
        OpportunityStatus.ACTIVE,
        occurred_at=NOW + timedelta(minutes=2),
        reason="Entry trigger confirmed",
        actor="signal-evaluator",
    )
    cancelled = watching.transition_to(
        OpportunityStatus.CANCELLED,
        occurred_at=NOW + timedelta(minutes=3),
        reason="Operator cancelled setup",
        actor="owner",
    )
    store.append_transition(active, expected_status=OpportunityStatus.WATCHING)

    with pytest.raises(OpportunityStateConflict, match="state changed"):
        store.append_transition(cancelled, expected_status=OpportunityStatus.WATCHING)

    current = store.get(opportunity.opportunity_id)
    assert current is not None
    assert current.status is OpportunityStatus.ACTIVE
    assert len(current.lifecycle_events) == 2


def test_list_by_status_is_bounded_and_validates_limit(tmp_path) -> None:
    store = SQLiteTradingOpportunityStore(tmp_path / "opportunities.db")
    first = make_opportunity()
    second = make_opportunity()
    store.create(first)
    store.create(second)

    assert len(store.list_by_status((OpportunityStatus.DRAFT,), limit=1)) == 1
    assert store.list_by_status((), limit=10) == ()
    with pytest.raises(ValueError, match="limit must be positive"):
        store.list_by_status((OpportunityStatus.DRAFT,), limit=0)
