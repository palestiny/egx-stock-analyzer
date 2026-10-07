from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid5

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.opportunity.classification import OpportunityClassification
from app.domain.technical_analysis.scoring import TechnicalScore
from app.infrastructure.synthetic_market.feature_harness import (
    SyntheticFeatureReport,
    SyntheticFeatureSnapshot,
)
from app.infrastructure.synthetic_market.generator import (
    SyntheticDataset,
    SyntheticScenario,
    SyntheticSymbolSeries,
)
from app.infrastructure.synthetic_market.opportunity_harness import (
    SyntheticOpportunityHarness,
)
from app.infrastructure.synthetic_market.quality_harness import (
    SyntheticQualityReport,
    SyntheticQualitySnapshot,
)


def bars(stock_id):
    values = ("10", "9", "10", "11", "10")
    return tuple(
        PriceBar.create(
            stock_id=stock_id,
            timeframe=Timeframe.DAILY,
            timestamp=datetime(2025, 1, index + 1, tzinfo=timezone.utc),
            open=Price(Decimal(value)),
            high=Price(Decimal(value)),
            low=Price(Decimal(value)),
            close=Price(Decimal(value)),
            volume=Volume(100_000),
        )
        for index, value in enumerate(values)
    )


def dataset(symbol: str):
    stock_id = uuid5(UUID("3e4e7e7b-2c77-4baf-8c6b-5b4c8b1b0d51"), symbol)
    series = SyntheticSymbolSeries(
        symbol=symbol,
        stock_id=stock_id,
        bars=bars(stock_id),
        regimes=(),
    )
    return SyntheticDataset(
        scenario=SyntheticScenario("test", "controlled", 1, (symbol,), 5),
        series=(series,),
    ), stock_id


def run_for_total(total_score: int):
    dataset_value, stock_id = dataset(f"S{total_score}")
    features = SyntheticFeatureReport(
        scenario_name="test",
        seed=1,
        snapshots=(
            SyntheticFeatureSnapshot(
                symbol=f"S{total_score}",
                stock_id=stock_id,
                trend="uptrend",
                momentum="positive",
                momentum_percent=1.0,
                volume="above_average",
                volume_ratio=2.0,
                support_count=1,
                resistance_count=1,
                technical_score=1,
                regime="bull",
            ),
        ),
    )
    quality = SyntheticQualityReport(
        decision_date=date(2025, 1, 5),
        snapshots=(
            SyntheticQualitySnapshot(
                symbol=f"S{total_score}",
                stock_id=stock_id,
                decision_date=date(2025, 1, 5),
                fundamental_score=0,
                technical_score=total_score,
                total_score=total_score,
                current_period_end=date(2024, 12, 31),
                previous_period_end=date(2023, 12, 31),
            ),
        ),
    )
    return SyntheticOpportunityHarness().run(dataset_value, features, quality)


def test_harness_produces_two_point_entry_from_controlled_levels():
    report = run_for_total(4)
    snapshot = report.snapshots[0]

    assert snapshot.entry_quality_score.total_score == 2
    assert snapshot.entry_quality_score.support_points == 1
    assert snapshot.entry_quality_score.resistance_points == 1


def test_harness_preserves_existing_opportunity_classification_rules():
    assert run_for_total(-2).snapshots[0].classification is OpportunityClassification.AVOID
    assert run_for_total(0).snapshots[0].classification is OpportunityClassification.HOLD
    assert run_for_total(2).snapshots[0].classification is OpportunityClassification.WATCH
    assert run_for_total(4).snapshots[0].classification is OpportunityClassification.BUY


def test_harness_is_deterministic():
    first = run_for_total(4)
    second = run_for_total(4)

    assert first == second
    assert first.counts[OpportunityClassification.BUY] == 1
