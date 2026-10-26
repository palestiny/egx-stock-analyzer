from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.opportunity.trading_opportunity import (
    OpportunityEvidence,
    OpportunityStatus,
    OpportunityTarget,
    TradingOpportunity,
)


NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def make_opportunity(**overrides: object) -> TradingOpportunity:
    values: dict[str, object] = {
        "symbol": " comi ",
        "timeframe": " 1D ",
        "strategy_version": "entry-v1",
        "created_at": NOW,
        "expires_at": NOW + timedelta(days=10),
        "entry_low": Decimal("50.00"),
        "entry_high": Decimal("52.00"),
        "invalidation_price": Decimal("48.00"),
        "targets": (
            OpportunityTarget(Decimal("55.00"), "Prior resistance"),
            OpportunityTarget(Decimal("60.00"), "Measured move"),
        ),
        "evidence": (
            OpportunityEvidence(
                evidence_type="candle_rejection",
                description="Daily candle rejected a known support area",
                observed_at=NOW,
                source="daily_ohlcv",
                source_version="dataset-2026-10-26-v1",
            ),
        ),
    }
    values.update(overrides)
    return TradingOpportunity.create(**values)  # type: ignore[arg-type]


def test_create_normalizes_symbol_and_timeframe_and_starts_as_draft() -> None:
    opportunity = make_opportunity()

    assert opportunity.symbol == "COMI"
    assert opportunity.timeframe == "1d"
    assert opportunity.status is OpportunityStatus.DRAFT
    assert opportunity.version == 1
    assert opportunity.lifecycle_events == ()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"symbol": "  "}, "symbol is required"),
        ({"timeframe": " "}, "timeframe is required"),
        ({"strategy_version": " "}, "strategy_version is required"),
        ({"expires_at": NOW}, "expires_at must be later than created_at"),
        ({"entry_low": Decimal("53")}, "entry_low must be less than or equal to entry_high"),
        (
            {"invalidation_price": Decimal("50")},
            "Long opportunity invalidation price must be below the entry zone",
        ),
        ({"targets": ()}, "At least one target is required"),
        ({"evidence": ()}, "At least one evidence item is required"),
    ],
)
def test_create_rejects_invalid_setup(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        make_opportunity(**overrides)


def test_create_requires_timezone_aware_timestamps() -> None:
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        make_opportunity(created_at=datetime(2026, 10, 26, 12, 0))


def test_create_rejects_targets_not_above_entry_zone() -> None:
    with pytest.raises(ValueError, match="targets must be above the entry zone"):
        make_opportunity(
            targets=(OpportunityTarget(Decimal("52"), "Not above entry"),)
        )


def test_transition_records_append_only_lifecycle_event() -> None:
    original = make_opportunity()
    watching = original.transition_to(
        OpportunityStatus.WATCHING,
        occurred_at=NOW + timedelta(minutes=1),
        reason="Setup meets the configured watch rules",
        actor="signal-evaluator",
        evidence_version="dataset-2026-10-26-v1",
    )
    active = watching.transition_to(
        OpportunityStatus.ACTIVE,
        occurred_at=NOW + timedelta(minutes=2),
        reason="Entry trigger confirmed at candle close",
        actor="signal-evaluator",
        evidence_version="dataset-2026-10-26-v1",
    )

    assert original.status is OpportunityStatus.DRAFT
    assert original.lifecycle_events == ()
    assert watching.status is OpportunityStatus.WATCHING
    assert len(watching.lifecycle_events) == 1
    assert active.status is OpportunityStatus.ACTIVE
    assert len(active.lifecycle_events) == 2
    assert active.lifecycle_events[0].to_status is OpportunityStatus.WATCHING
    assert active.lifecycle_events[1].from_status is OpportunityStatus.WATCHING
    assert active.lifecycle_events[1].to_status is OpportunityStatus.ACTIVE
    assert active.lifecycle_events[1].evidence_version == "dataset-2026-10-26-v1"


def test_transition_rejects_skipping_required_lifecycle_states() -> None:
    opportunity = make_opportunity()

    with pytest.raises(ValueError, match="Transition from draft to active is not allowed"):
        opportunity.transition_to(
            OpportunityStatus.ACTIVE,
            occurred_at=NOW + timedelta(minutes=1),
            reason="Attempted to skip watch state",
            actor="test",
        )


def test_terminal_opportunity_cannot_be_reactivated() -> None:
    opportunity = make_opportunity().transition_to(
        OpportunityStatus.CANCELLED,
        occurred_at=NOW + timedelta(minutes=1),
        reason="Operator cancelled setup",
        actor="owner",
    )

    with pytest.raises(ValueError, match="Transition from cancelled to active is not allowed"):
        opportunity.transition_to(
            OpportunityStatus.ACTIVE,
            occurred_at=NOW + timedelta(minutes=2),
            reason="Should not be allowed",
            actor="test",
        )


def test_transition_rejects_empty_reason_and_naive_timestamp() -> None:
    opportunity = make_opportunity()

    with pytest.raises(ValueError, match="Transition reason is required"):
        opportunity.transition_to(
            OpportunityStatus.WATCHING,
            occurred_at=NOW + timedelta(minutes=1),
            reason=" ",
            actor="test",
        )

    with pytest.raises(ValueError, match="occurred_at must be timezone-aware"):
        opportunity.transition_to(
            OpportunityStatus.WATCHING,
            occurred_at=datetime(2026, 10, 26, 12, 1),
            reason="Valid reason",
            actor="test",
        )


def test_data_unreliable_can_be_recovered_after_evidence_is_validated() -> None:
    opportunity = make_opportunity().transition_to(
        OpportunityStatus.DATA_UNRELIABLE,
        occurred_at=NOW + timedelta(minutes=1),
        reason="Required source data is stale",
        actor="data-quality-monitor",
    )

    recovered = opportunity.transition_to(
        OpportunityStatus.WATCHING,
        occurred_at=NOW + timedelta(minutes=2),
        reason="Source data was revalidated",
        actor="data-quality-monitor",
        evidence_version="dataset-2026-10-26-v2",
    )

    assert recovered.status is OpportunityStatus.WATCHING
    assert len(recovered.lifecycle_events) == 2
