from datetime import date, datetime, timezone
from decimal import Decimal

from app.infrastructure.synthetic_market.generator import SyntheticMarketGenerator
from app.infrastructure.synthetic_market.research_scenarios import (
    SyntheticEventType,
    SyntheticResearchScenarioBuilder,
)


def test_research_scenario_contains_pit_financials_events_and_relationships():
    dataset = SyntheticMarketGenerator().generate(
        symbols=("COMI", "EGAL", "SWDY", "ETEL"),
        bars_per_symbol=800,
        seed=61001,
    )
    scenario = SyntheticResearchScenarioBuilder().build(dataset)

    assert len(scenario.financial_snapshots) == 20
    assert all(
        snapshot.available_at.tzinfo is not None
        and snapshot.available_at.date() >= snapshot.period_end
        for snapshot in scenario.financial_snapshots
    )
    assert any(event.event_type is SyntheticEventType.VOLUME_SPIKE for event in scenario.events)
    assert any(event.event_type is SyntheticEventType.MARKET_CRASH for event in scenario.events)
    assert len(scenario.relationships) == 2


def test_financial_snapshot_rejects_pre_period_availability():
    from app.infrastructure.synthetic_market.research_scenarios import SyntheticFinancialSnapshot

    try:
        SyntheticFinancialSnapshot(
            stock_id=dataset_stock_id(),
            period_end=date(2025, 12, 31),
            available_at=datetime(2025, 12, 30, tzinfo=timezone.utc),
            revenue=Decimal("1"),
            net_income=Decimal("1"),
            current_assets=Decimal("1"),
            current_liabilities=Decimal("1"),
            source="synthetic-fixture",
            revision="v1",
        )
        assert False, "expected ValueError"
    except ValueError:
        pass


def dataset_stock_id():
    return SyntheticMarketGenerator().generate(
        symbols=("COMI",), bars_per_symbol=30, seed=1
    ).series[0].stock_id
