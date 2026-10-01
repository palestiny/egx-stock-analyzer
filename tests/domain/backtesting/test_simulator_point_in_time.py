from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domain.backtesting.simulator import (
    BacktestConfiguration,
    BacktestSimulator,
    BacktestStrategy,
)
from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.stocks.stock import Stock


STOCK = Stock.create(symbol="TIMING", name="Backtest Timing Stock")


def bar(index: int, open_price: str, close_price: str) -> PriceBar:
    return PriceBar.create(
        stock_id=STOCK.id,
        timeframe=Timeframe.DAILY,
        timestamp=datetime(2026, 2, 1, tzinfo=timezone.utc) + timedelta(days=index),
        open=Price(Decimal(open_price)),
        high=Price(Decimal(open_price)),
        low=Price(Decimal(open_price)),
        close=Price(Decimal(close_price)),
        volume=Volume(1000),
    )


def configuration() -> BacktestConfiguration:
    return BacktestConfiguration(
        max_holding_bars=10,
        transaction_cost_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
    )


def test_signal_is_point_in_time_and_entry_uses_next_bar_open():
    bars = [
        bar(0, "100", "101"),
        bar(1, "101", "102"),
        bar(2, "102", "103"),
        bar(3, "110", "111"),
        bar(4, "120", "121"),
        bar(5, "130", "131"),
        bar(6, "140", "141"),
    ]
    observed = []

    def signal(history):
        observed.append((history[-1].timestamp, len(history), tuple(item.timestamp for item in history)))
        return len(history) == 3

    strategy = BacktestStrategy(
        strategy_id="timing",
        version="1",
        signal=signal,
        position_valid=lambda history: len(history) < 5,
    )

    result = BacktestSimulator.run(bars, strategy, configuration())

    assert observed == [
        (bars[0].timestamp, 1, (bars[0].timestamp,)),
        (bars[1].timestamp, 2, (bars[0].timestamp, bars[1].timestamp)),
        (bars[2].timestamp, 3, (bars[0].timestamp, bars[1].timestamp, bars[2].timestamp)),
    ]
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.signal_timestamp == bars[2].timestamp
    assert trade.execution_timestamp == bars[3].timestamp
    assert trade.gross_entry_price == bars[3].open
    assert trade.exit_timestamp == bars[5].timestamp
    assert trade.gross_exit_price == bars[5].open


def test_repeated_run_with_identical_inputs_is_deterministic():
    bars = [
        bar(0, "100", "101"),
        bar(1, "101", "102"),
        bar(2, "102", "103"),
        bar(3, "110", "111"),
        bar(4, "120", "121"),
        bar(5, "130", "131"),
        bar(6, "140", "141"),
    ]
    strategy = BacktestStrategy(
        strategy_id="deterministic",
        version="1",
        signal=lambda history: len(history) == 3,
        position_valid=lambda history: len(history) < 5,
    )

    first = BacktestSimulator.run(bars, strategy, configuration())
    second = BacktestSimulator.run(bars, strategy, configuration())

    assert first == second
    assert first.metrics == second.metrics
