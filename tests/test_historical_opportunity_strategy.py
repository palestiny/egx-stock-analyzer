from datetime import date, datetime, timezone
from decimal import Decimal

from app.application.analysis.input_assembler import AnalysisInputAssemblyPolicy
from app.application.backtesting.historical_opportunity_strategy import (
    HistoricalOpportunityClassificationBacktestStrategy,
)
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.fundamental_analysis.historical_financial_snapshot import (
    HistoricalFinancialSnapshot,
)
from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.opportunity.classification import OpportunityClassification
from app.domain.opportunity.classification import OpportunityClassificationResult
from app.domain.stocks.stock import Stock


def make_bar(stock_id, day: int) -> PriceBar:
    return PriceBar.create(
        stock_id=stock_id,
        timeframe=Timeframe.DAILY,
        timestamp=datetime(2026, 9, day, tzinfo=timezone.utc),
        open=Price(Decimal("100")),
        high=Price(Decimal("101")),
        low=Price(Decimal("99")),
        close=Price(Decimal("100")),
        volume=Volume(1000),
    )


class FakeFundamentalProvider:
    def __init__(self) -> None:
        self.calls = []

    def get_periods(self, stock, as_of):
        self.calls.append((stock, as_of))
        return (
            FinancialPeriod(date(2026, 6, 30), Decimal("100"), Decimal("10")),
            FinancialPeriod(date(2026, 3, 31), Decimal("90"), Decimal("8")),
        )


def test_historical_strategy_uses_completed_bar_date_for_point_in_time_fundamentals():
    stock = Stock.create("EGAL", "Egypt Aluminium")
    fundamentals = FakeFundamentalProvider()
    captured = []

    def analyze(
        stock_id,
        timeframe,
        price_bars,
        current_period,
        previous_period,
        momentum_lookback,
        volume_lookback,
    ):
        captured.append(
            (
                stock_id,
                timeframe,
                price_bars,
                current_period,
                previous_period,
                momentum_lookback,
                volume_lookback,
            )
        )
        return type(
            "Result",
            (),
            {
                "opportunity": OpportunityClassificationResult(
                    classification=OpportunityClassification.BUY,
                    reason="test",
                )
            },
        )()

    strategy = HistoricalOpportunityClassificationBacktestStrategy(
        stock,
        fundamentals,
        AnalysisInputAssemblyPolicy(momentum_lookback=3, volume_lookback=4),
        analyze=analyze,
    ).to_backtest_strategy()

    bars = [make_bar(stock.id, 18), make_bar(stock.id, 19)]
    assert strategy.signal(bars) is True

    assert fundamentals.calls == [(stock, date(2026, 9, 19))]
    assert captured[0][0] == stock.id
    assert captured[0][1] is Timeframe.DAILY
    assert captured[0][2] == bars
    assert captured[0][5:] == (3, 4)


def test_historical_strategy_preserves_production_opportunity_classification():
    stock = Stock.create("EGAL", "Egypt Aluminium")
    fundamentals = FakeFundamentalProvider()

    def analyze(*args):
        return type(
            "Result",
            (),
            {
                "opportunity": OpportunityClassificationResult(
                    classification=OpportunityClassification.WATCH,
                    reason="test",
                )
            },
        )()

    strategy = HistoricalOpportunityClassificationBacktestStrategy(
        stock,
        fundamentals,
        analyze=analyze,
    ).to_backtest_strategy()

    assert strategy.signal([make_bar(stock.id, 19)]) is False


def test_historical_strategy_identity_matches_strategy_v0():
    stock = Stock.create("EGAL", "Egypt Aluminium")
    strategy = HistoricalOpportunityClassificationBacktestStrategy(
        stock,
        FakeFundamentalProvider(),
        analyze=lambda *args: None,
    ).to_backtest_strategy()

    assert strategy.strategy_id == "opportunity-classification"
    assert strategy.version == "0"
