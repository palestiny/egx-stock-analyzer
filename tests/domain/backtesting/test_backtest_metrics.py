from decimal import Decimal

from app.domain.backtesting.simulator import (
    BacktestConfiguration,
    BacktestResult,
    BacktestTrade,
    ExitReason,
)
from app.domain.market_data.price import Price


CONFIGURATION = BacktestConfiguration(
    max_holding_bars=10,
    transaction_cost_rate=Decimal("0"),
    slippage_rate=Decimal("0"),
)


def _trade(net_return: str) -> BacktestTrade:
    value = Decimal("10")
    return BacktestTrade(
        strategy_id="test",
        strategy_version="1",
        signal_timestamp=None,
        execution_timestamp=None,
        entry_price=Price(value),
        gross_entry_price=Price(value),
        exit_timestamp=None,
        exit_price=Price(value),
        gross_exit_price=Price(value),
        exit_reason=ExitReason.TIME_LIMIT,
        gross_return=Decimal(net_return),
        total_cost=Decimal("0"),
        net_return=Decimal(net_return),
    )


def test_metrics_include_profit_factor_average_outcomes_and_equity_drawdown() -> None:
    result = BacktestResult(
        strategy_id="test",
        strategy_version="1",
        configuration=CONFIGURATION,
        trades=tuple(_trade(value) for value in ("0.10", "-0.05", "0.02", "-0.10")),
        open_trade_count=0,
    )

    metrics = result.metrics

    assert metrics.profit_factor == Decimal("0.8")
    assert metrics.average_winning_return == Decimal("0.06")
    assert metrics.average_losing_return == Decimal("-0.075")
    assert metrics.max_drawdown == Decimal("0.95931") / Decimal("1.1") - Decimal("1")


def test_metrics_define_empty_and_no_loss_cases_without_infinity() -> None:
    empty = BacktestResult(
        strategy_id="test",
        strategy_version="1",
        configuration=CONFIGURATION,
        trades=(),
        open_trade_count=0,
    ).metrics
    no_losses = BacktestResult(
        strategy_id="test",
        strategy_version="1",
        configuration=CONFIGURATION,
        trades=(_trade("0.05"), _trade("0.02")),
        open_trade_count=0,
    ).metrics

    assert empty.profit_factor is None
    assert empty.max_drawdown == Decimal("0")
    assert empty.average_winning_return is None
    assert empty.average_losing_return is None
    assert no_losses.profit_factor is None
    assert no_losses.average_losing_return is None
    assert no_losses.max_drawdown == Decimal("0")
