from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.application.backtesting.opportunity_strategy import (
    OpportunityClassificationBacktestStrategy,
)
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.price import Price
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.opportunity.classification import OpportunityClassification


def make_bar(day: int) -> PriceBar:
    return PriceBar.create(
        stock_id=uuid4(),
        timeframe=Timeframe.DAILY,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day - 1),
        open=Price(Decimal("100")),
        high=Price(Decimal("101")),
        low=Price(Decimal("99")),
        close=Price(Decimal("100")),
        volume=Volume(1000),
    )


def test_opportunity_backtest_strategy_delegates_signal_to_production_result():
    observed_histories = []

    def analyze(history):
        observed_histories.append(history)
        return SimpleNamespace(
            opportunity=SimpleNamespace(
                classification=OpportunityClassification.BUY
            )
        )

    strategy = OpportunityClassificationBacktestStrategy(analyze).to_backtest_strategy()
    bars = [make_bar(1)]

    assert strategy.signal(bars) is True
    assert strategy.position_valid(bars) is True
    assert observed_histories == [bars, bars]


def test_opportunity_backtest_strategy_does_not_reimplement_classification_rules():
    def analyze(history):
        return SimpleNamespace(
            opportunity=SimpleNamespace(
                classification=OpportunityClassification.WATCH
            )
        )

    strategy = OpportunityClassificationBacktestStrategy(analyze).to_backtest_strategy()

    assert strategy.signal([make_bar(1)]) is False
    assert strategy.position_valid([make_bar(1)]) is False


def test_strategy_identity_is_stable():
    strategy = OpportunityClassificationBacktestStrategy(lambda history: None).to_backtest_strategy()

    assert strategy.strategy_id == "opportunity-classification"
    assert strategy.version == "0"
