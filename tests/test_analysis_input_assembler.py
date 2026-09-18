from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.analysis.input_assembler import (
    AnalysisInputAssembler,
    AnalysisInputAssemblyPolicy,
)
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock


class FakeMarketDataProvider:
    def __init__(self, observations):
        self.observations = observations
        self.calls = []

    def get_daily_observations(self, stock, from_date, to_date):
        self.calls.append((stock, from_date, to_date))
        return self.observations


class FakeFundamentalDataProvider:
    def __init__(self, current_period, previous_period):
        self.current_period = current_period
        self.previous_period = previous_period
        self.calls = []

    def get_periods(self, stock, as_of):
        self.calls.append((stock, as_of))
        return self.current_period, self.previous_period


def make_observation(stock_id, timestamp, close="101"):
    return RawPriceBarObservation(
        stock_id=stock_id,
        timeframe=Timeframe.DAILY,
        timestamp=timestamp,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal(close),
        volume=1000,
    )


def make_periods():
    return (
        FinancialPeriod(date(2026, 9, 15), Decimal("100"), Decimal("10"), Decimal("40"), Decimal("20")),
        FinancialPeriod(date(2026, 6, 30), Decimal("90"), Decimal("8"), Decimal("35"), Decimal("18")),
    )


def test_assembler_builds_stock_analysis_input_from_acquired_data():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    market = FakeMarketDataProvider(
        [
            make_observation(
                stock.id,
                datetime(2026, 9, 15, tzinfo=timezone.utc) - timedelta(days=offset),
            )
            for offset in range(11)
        ]
    )
    current_period, previous_period = make_periods()
    fundamentals = FakeFundamentalDataProvider(current_period, previous_period)
    policy = AnalysisInputAssemblyPolicy(
        momentum_lookback=5,
        volume_lookback=10,
        market_data_window_days=30,
    )

    result = AnalysisInputAssembler(market, fundamentals, policy).assemble(
        stock,
        date(2026, 9, 16),
    )

    assert result.symbol == "EGAL"
    assert result.stock_id == stock.id
    assert result.timeframe is Timeframe.DAILY
    assert len(result.price_bars) == 11
    assert result.current_period is current_period
    assert result.previous_period is previous_period
    assert result.momentum_lookback == 5
    assert result.volume_lookback == 10

    assert market.calls == [(stock, date(2026, 8, 17), date(2026, 9, 16))]
    assert fundamentals.calls == [(stock, date(2026, 9, 16))]


def test_assembler_rejects_empty_market_data():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    market = FakeMarketDataProvider([])
    current_period, previous_period = make_periods()
    fundamentals = FakeFundamentalDataProvider(current_period, previous_period)

    with pytest.raises(ValueError, match="no observations"):
        AnalysisInputAssembler(market, fundamentals).assemble(
            stock,
            date(2026, 9, 16),
        )


def test_assembler_rejects_invalid_market_data():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    invalid = RawPriceBarObservation(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        timestamp=datetime(2026, 9, 15, tzinfo=timezone.utc),
        open=Decimal("100"),
        high=Decimal("98"),
        low=Decimal("99"),
        close=Decimal("101"),
        volume=1000,
    )
    market = FakeMarketDataProvider([invalid])
    current_period, previous_period = make_periods()
    fundamentals = FakeFundamentalDataProvider(current_period, previous_period)

    with pytest.raises(ValueError, match="Insufficient valid market data observations"):
        AnalysisInputAssembler(market, fundamentals).assemble(
            stock,
            date(2026, 9, 16),
        )


def test_assembly_policy_rejects_non_positive_lookbacks():
    with pytest.raises(ValueError, match="momentum_lookback"):
        AnalysisInputAssemblyPolicy(momentum_lookback=0)

    with pytest.raises(ValueError, match="volume_lookback"):
        AnalysisInputAssemblyPolicy(volume_lookback=0)

    with pytest.raises(ValueError, match="market_data_window_days"):
        AnalysisInputAssemblyPolicy(market_data_window_days=0)
