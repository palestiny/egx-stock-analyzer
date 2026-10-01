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


STOCK = Stock.create(symbol="TEST", name="Backtest Test Stock")


def bar(index: int, open_price: str, close_price: str) -> PriceBar:
    return PriceBar.create(
        stock_id=STOCK.id,
        timeframe=Timeframe.DAILY,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index),
        open=Price(Decimal(open_price)),
        high=Price(Decimal(open_price)),
        low=Price(Decimal(open_price)),
        close=Price(Decimal(close_price)),
        volume=Volume(1000),
    )


def test_warmup_bars_build_history_before_first_evaluated_signal():
    bars = [
        bar(0, "100", "101"),
        bar(1, "101", "102"),
        bar(2, "102", "103"),
        bar(3, "110", "111"),
        bar(4, "120", "121"),
        bar(5, "130", "131"),
    ]
    observed_history_lengths = []

    def signal(history):
        observed_history_lengths.append(len(history))
        return len(history) in {1, 4}

    strategy = BacktestStrategy(
        strategy_id="warmup",
        version="1",
        signal=signal,
        position_valid=lambda history: len(history) < 6,
    )

    result = BacktestSimulator.run(
        bars,
        strategy,
        BacktestConfiguration(
            max_holding_bars=3,
            transaction_cost_rate=Decimal("0"),
            slippage_rate=Decimal("0"),
            warmup_bars=3,
        ),
    )

    assert observed_history_lengths == [4]
    assert len(result.trades) == 0
    assert result.open_trade_count == 1


def test_negative_warmup_bars_are_rejected():
    bars = [bar(0, "100", "101")]
    strategy = BacktestStrategy(
        strategy_id="invalid-warmup",
        version="1",
        signal=lambda history: False,
        position_valid=lambda history: True,
    )

    try:
        BacktestSimulator.run(
            bars,
            strategy,
            BacktestConfiguration(
                max_holding_bars=1,
                transaction_cost_rate=Decimal("0"),
                slippage_rate=Decimal("0"),
                warmup_bars=-1,
            ),
        )
        assert False, "expected ValueError"
    except ValueError:
        pass
