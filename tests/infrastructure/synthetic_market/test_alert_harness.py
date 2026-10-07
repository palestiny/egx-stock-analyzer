from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid5

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.opportunity.classification import OpportunityClassification
from app.domain.technical_analysis.scoring import TechnicalScore
from app.infrastructure.synthetic_market.alert_harness import SyntheticAlertHarness
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
from app.infrastructure.synthetic_market.stress_harness import SyntheticStressHarness


NAMESPACE = UUID("3e4e7e7b-2c77-4baf-8c6b-5b4c8b1b0d51")


def _bars(stock_id):
    return tuple(
        PriceBar.create(
            stock_id=stock_id,
            timeframe=Timeframe.DAILY,
            timestamp=datetime(2025, 1, index + 1, tzinfo=timezone.utc),
            open=Price(Decimal(value)),
            high=Price(Decimal(value)),
            low=Price(Decimal(value)),
            close=Price(Decimal(value)),
            volume=Volume(volume),
        )
        for index, (value, volume) in enumerate(
            (("10", 100_000), ("9", 100_000), ("10", 100_000),
             ("11", 100_000), ("10", 100_000))
        )
    )


def _dataset():
    symbol = "TEST"
    stock_id = uuid5(NAMESPACE, symbol)
    series = SyntheticSymbolSeries(
        symbol=symbol,
        stock_id=stock_id,
        bars=_bars(stock_id),
        regimes=(),
    )
    return SyntheticDataset(
        scenario=SyntheticScenario("test-alerts", "controlled", 61001, (symbol,), 5),
        series=(series,),
    ), stock_id


def _opportunity(dataset_value, stock_id):
    features = SyntheticFeatureReport(
        scenario_name="test-alerts",
        seed=61001,
        snapshots=(
            SyntheticFeatureSnapshot(
                symbol="TEST",
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
        decision_date=__import__("datetime").date(2025, 1, 5),
        snapshots=(
            SyntheticQualitySnapshot(
                symbol="TEST",
                stock_id=stock_id,
                decision_date=__import__("datetime").date(2025, 1, 5),
                fundamental_score=0,
                technical_score=4,
                total_score=4,
                current_period_end=__import__("datetime").date(2024, 12, 31),
                previous_period_end=__import__("datetime").date(2023, 12, 31),
            ),
        ),
    )
    return SyntheticOpportunityHarness().run(dataset_value, features, quality)


def test_alert_harness_emits_buy_alert_for_existing_buy_classification():
    dataset_value, stock_id = _dataset()
    opportunity = _opportunity(dataset_value, stock_id)
    stress = SyntheticStressHarness().run(dataset_value)

    report = SyntheticAlertHarness().run(dataset_value, opportunity, stress)

    assert opportunity.snapshots[0].classification is OpportunityClassification.BUY
    assert len(report.candidates) == 1
    assert any("BUY opportunity" in event.message for event in report.events)


def test_alert_harness_is_deterministic():
    dataset_value, stock_id = _dataset()
    opportunity = _opportunity(dataset_value, stock_id)
    stress = SyntheticStressHarness().run(dataset_value)

    first = SyntheticAlertHarness().run(dataset_value, opportunity, stress)
    second = SyntheticAlertHarness().run(dataset_value, opportunity, stress)

    assert first == second


def test_alert_events_have_stable_signal_identity_and_trigger_type():
    dataset_value, stock_id = _dataset()
    opportunity = _opportunity(dataset_value, stock_id)
    stress = SyntheticStressHarness().run(dataset_value)

    report = SyntheticAlertHarness().run(dataset_value, opportunity, stress)

    assert report.events
    assert all(event.symbol == "TEST" for event in report.events)
    assert all(event.event_type.value == "SIGNAL_TRIGGERED" for event in report.events)
    assert len({event.signal_id for event in report.events}) == len(report.events)
