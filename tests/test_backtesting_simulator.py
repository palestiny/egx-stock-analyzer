from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.domain.backtesting.simulator import (
    BacktestConfiguration,
    BacktestSimulator,
    BacktestStrategy,
    ExitReason,
)
from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume


STOCK_ID = uuid4()
START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def bar(day: int, open_: str, close: str) -> PriceBar:
    return PriceBar.create(
        stock_id=STOCK_ID,
        timeframe=Timeframe.DAILY,
        timestamp=START + timedelta(days=day),
        open=Price(Decimal(open_)),
        high=Price(max(Decimal(open_), Decimal(close))),
        low=Price(min(Decimal(open_), Decimal(close))),
        close=Price(Decimal(close)),
        volume=Volume(1000),
    )


def config(max_holding_bars: int = 3) -> BacktestConfiguration:
    return BacktestConfiguration(
        max_holding_bars=max_holding_bars,
        transaction_cost_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
    )


def test_entry_is_generated_from_completed_bar_and_executes_next_bar_open():
    bars = [
        bar(0, "100", "105"),
        bar(1, "110", "111"),
        bar(2, "120", "121"),
        bar(3, "130", "131"),
    ]

    strategy = BacktestStrategy(
        strategy_id="opportunity-classification",
        version="0",
        signal=lambda history: len(history) == 1,
        position_valid=lambda history: len(history) < 3,
    )

    result = BacktestSimulator.run(bars, strategy, config())

    trade = result.trades[0]
    assert trade.signal_timestamp == bars[0].timestamp
    assert trade.execution_timestamp == bars[1].timestamp
    assert trade.entry_price == bars[1].open


def test_strategy_invalidation_exits_on_next_bar_open():
    bars = [
        bar(0, "100", "105"),
        bar(1, "110", "111"),
        bar(2, "120", "115"),
        bar(3, "90", "92"),
    ]

    strategy = BacktestStrategy(
        strategy_id="opportunity-classification",
        version="0",
        signal=lambda history: len(history) == 1,
        position_valid=lambda history: len(history) < 3,
    )

    result = BacktestSimulator.run(bars, strategy, config())

    trade = result.trades[0]
    assert trade.exit_reason is ExitReason.STRATEGY_INVALIDATION
    assert trade.exit_timestamp == bars[3].timestamp
    assert trade.exit_price == bars[3].open


def test_time_based_exit_is_applied_when_strategy_remains_valid():
    bars = [
        bar(0, "100", "105"),
        bar(1, "110", "111"),
        bar(2, "120", "121"),
        bar(3, "130", "131"),
    ]

    strategy = BacktestStrategy(
        strategy_id="opportunity-classification",
        version="0",
        signal=lambda history: len(history) == 1,
        position_valid=lambda history: True,
    )

    result = BacktestSimulator.run(
        bars,
        strategy,
        config(max_holding_bars=2),
    )

    trade = result.trades[0]
    assert trade.exit_reason is ExitReason.TIME_LIMIT
    assert trade.exit_timestamp == bars[3].timestamp
    assert trade.exit_price == bars[3].open


def test_missing_exit_bar_leaves_trade_open_instead_of_inventing_execution():
    bars = [bar(0, "100", "105"), bar(1, "110", "111")]

    strategy = BacktestStrategy(
        strategy_id="opportunity-classification",
        version="0",
        signal=lambda history: len(history) == 1,
        position_valid=lambda history: True,
    )

    result = BacktestSimulator.run(
        bars,
        strategy,
        config(max_holding_bars=1),
    )

    assert result.trades == ()
    assert result.open_trade_count == 1


def test_cost_and_slippage_are_explicitly_applied():
    bars = [
        bar(0, "100", "105"),
        bar(1, "110", "111"),
        bar(2, "121", "122"),
        bar(3, "130", "131"),
    ]

    strategy = BacktestStrategy(
        strategy_id="opportunity-classification",
        version="0",
        signal=lambda history: len(history) == 1,
        position_valid=lambda history: len(history) < 3,
    )

    result = BacktestSimulator.run(
        bars,
        strategy,
        BacktestConfiguration(
            max_holding_bars=3,
            transaction_cost_rate=Decimal("0.01"),
            slippage_rate=Decimal("0.01"),
        ),
    )

    trade = result.trades[0]
    assert trade.gross_entry_price == bars[1].open
    assert trade.gross_exit_price == bars[3].open
    assert trade.total_cost > Decimal("0")
    assert trade.net_return < trade.gross_return


def test_strategy_identity_and_configuration_are_preserved():
    bars = [
        bar(0, "100", "105"),
        bar(1, "110", "111"),
        bar(2, "120", "121"),
        bar(3, "130", "131"),
    ]
    strategy = BacktestStrategy(
        strategy_id="trend-invalidation",
        version="1.2",
        signal=lambda history: len(history) == 1,
        position_valid=lambda history: len(history) < 3,
    )
    configuration = config()

    result = BacktestSimulator.run(bars, strategy, configuration)

    assert result.strategy_id == "trend-invalidation"
    assert result.strategy_version == "1.2"
    assert result.configuration == configuration


def test_same_inputs_strategy_and_configuration_are_deterministic():
    bars = [
        bar(0, "100", "105"),
        bar(1, "110", "111"),
        bar(2, "120", "121"),
        bar(3, "130", "131"),
    ]
    strategy = BacktestStrategy(
        strategy_id="deterministic",
        version="1",
        signal=lambda history: len(history) == 1,
        position_valid=lambda history: len(history) < 3,
    )
    configuration = config()

    first = BacktestSimulator.run(bars, strategy, configuration)
    second = BacktestSimulator.run(bars, strategy, configuration)

    assert first == second


def test_future_bars_are_not_visible_to_signal_or_invalidation_callbacks():
    bars = [
        bar(0, "100", "105"),
        bar(1, "110", "111"),
        bar(2, "120", "121"),
        bar(3, "130", "131"),
    ]
    observed_lengths = []

    def signal(history):
        observed_lengths.append(len(history))
        return len(history) == 1

    strategy = BacktestStrategy(
        strategy_id="point-in-time",
        version="1",
        signal=signal,
        position_valid=lambda history: True,
    )

    BacktestSimulator.run(bars, strategy, config())

    assert observed_lengths[0] == 1


def test_no_signal_produces_empty_result():
    bars = [bar(0, "100", "105"), bar(1, "110", "111"), bar(2, "120", "121")]
    strategy = BacktestStrategy(
        strategy_id="none",
        version="1",
        signal=lambda history: False,
        position_valid=lambda history: True,
    )

    result = BacktestSimulator.run(bars, strategy, config())

    assert result.trades == ()
    assert result.open_trade_count == 0
    assert result.completed_trade_count == 0


def test_invalid_configuration_is_rejected():
    bars = [bar(0, "100", "105"), bar(1, "110", "111")]
    strategy = BacktestStrategy(
        strategy_id="invalid-config",
        version="1",
        signal=lambda history: True,
        position_valid=lambda history: True,
    )

    try:
        BacktestSimulator.run(
            bars,
            strategy,
            BacktestConfiguration(
                max_holding_bars=0,
                transaction_cost_rate=Decimal("0"),
                slippage_rate=Decimal("0"),
            ),
        )
        assert False, "expected ValueError"
    except ValueError:
        pass



def test_backtest_result_exposes_deterministic_aggregate_metrics():
    bars = [
        make_bar(1, "100", "100", "100"),
        make_bar(2, "100", "100", "100"),
        make_bar(3, "110", "110", "110"),
        make_bar(4, "110", "110", "110"),
    ]
    strategy = BacktestStrategy(
        strategy_id="metrics",
        version="1",
        signal=lambda history: len(history) == 1,
        position_valid=lambda history: len(history) < 3,
    )
    result = BacktestSimulator.run(
        bars,
        strategy,
        BacktestConfiguration(
            max_holding_bars=10,
            transaction_cost_rate=Decimal("0"),
            slippage_rate=Decimal("0"),
        ),
    )

    metrics = result.metrics
    assert metrics.completed_trade_count == 1
    assert metrics.open_trade_count == 0
    assert metrics.winning_trade_count == 1
    assert metrics.losing_trade_count == 0
    assert metrics.win_rate == Decimal("1")
    assert metrics.average_gross_return == Decimal("0.1")
    assert metrics.average_net_return == Decimal("0.1")
    assert metrics.cumulative_net_return == Decimal("0.1")
