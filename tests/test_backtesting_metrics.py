from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.domain.backtesting.evaluator import BacktestEvaluator
from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.opportunity.classification import OpportunityClassification


STOCK_ID = uuid4()
START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def price_bar(day: int, close: str) -> PriceBar:
    value = Price(Decimal(close))
    return PriceBar.create(
        stock_id=STOCK_ID,
        timeframe=Timeframe.DAILY,
        timestamp=START + timedelta(days=day),
        open=value,
        high=value,
        low=value,
        close=value,
        volume=Volume(1000),
    )


def test_backtest_metrics_summarize_evaluable_buy_outcomes():
    price_bars = [
        price_bar(0, "100"),
        price_bar(1, "110"),
        price_bar(2, "99"),
        price_bar(3, "132"),
    ]

    def strategy(history: list[PriceBar]) -> OpportunityClassification:
        return (
            OpportunityClassification.BUY
            if history[-1].timestamp in {START, START + timedelta(days=1)}
            else OpportunityClassification.HOLD
        )

    result = BacktestEvaluator.evaluate(
        price_bars=price_bars,
        strategy=strategy,
        forward_window=2,
    )

    assert result.buy_signal_count == 2
    assert result.positive_outcome_count == 1
    assert result.negative_outcome_count == 1
    assert result.win_rate == Decimal("0.5")
    assert result.average_forward_return == Decimal("0.1166666666666666666666666667")
    assert result.median_forward_return == Decimal("0.1166666666666666666666666667")
    assert result.minimum_forward_return == Decimal("-0.1")
    assert result.maximum_forward_return == Decimal("0.3333333333333333333333333333")
