from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.application.research.backtest import (
    BacktestStatus,
    EntryIntent,
    run_backtest,
)
from app.domain.research.dataset import (
    PriceAdjustment,
    ResearchBar,
    ResearchCostConfig,
    ResearchDataQuality,
    ResearchRunConfig,
)


def bar(day, *, open="100", high="105", low="95", close="100", provider="fixture", version="v1", quality=ResearchDataQuality.VALID, adjustment=PriceAdjustment.UNADJUSTED):
    timestamp = datetime(2026, 10, day, tzinfo=timezone.utc)
    return ResearchBar(
        "COMI", "1d", timestamp, timestamp, Decimal(open), Decimal(high), Decimal(low),
        Decimal(close), Decimal("1000"), provider, version, quality, adjustment,
    )


def config(*, provider="fixture", version="v1", adjustment=PriceAdjustment.UNADJUSTED, commission="0", slippage="0"):
    return ResearchRunConfig(
        dataset_version=version,
        provider=provider,
        strategy_id="test-strategy",
        strategy_version="1",
        evaluator_version="1",
        adjustment=adjustment,
        costs=ResearchCostConfig(Decimal(commission), Decimal(slippage)),
    )


def target_strategy(history):
    if len(history) == 1:
        return EntryIntent("LONG", Decimal("110"), Decimal("90"), "signal-1")
    return None


def test_entry_fills_at_next_open_and_target_closes_trade():
    bars = (
        bar(1),
        bar(2, open="100", high="112", low="98", close="111"),
        bar(3),
    )
    result = run_backtest(bars, config=config(), strategy=target_strategy, initial_capital=Decimal("1000"))

    assert result.status is BacktestStatus.COMPLETED
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.decision_timestamp == bars[0].source_timestamp
    assert trade.entry_timestamp == bars[1].source_timestamp
    assert trade.entry_price == Decimal("100")
    assert trade.exit_reason == "TARGET"
    assert trade.exit_price == Decimal("110")
    assert trade.net_pnl == Decimal("100")
    assert trade.quantity == Decimal("10")
    assert result.metrics.cumulative_net_return == Decimal("0.1")
    assert result.metrics.exposure_bars == 1
    assert result.metrics.total_bars == 3
    assert result.metrics.time_in_market_ratio == Decimal("1") / Decimal("3")


def test_signal_on_final_bar_is_recorded_unfilled():
    result = run_backtest((bar(1),), config=config(), strategy=target_strategy)
    assert result.status is BacktestStatus.COMPLETED
    assert not result.trades
    assert len(result.unfilled_decisions) == 1
    assert result.unfilled_decisions[0].reason == "signal on final bar has no next bar"


def test_strategy_only_receives_closed_prefix_and_future_mutation_does_not_change_earlier_entry():
    observed_lengths = []

    def strategy(history):
        observed_lengths.append(len(history))
        return target_strategy(history)

    original = (bar(1), bar(2, open="100", high="112", low="98", close="111"), bar(3))
    changed_future = (bar(1), bar(2, open="100", high="112", low="98", close="111"), bar(3, open="150", high="160", low="140", close="155"))
    first = run_backtest(original, config=config(), strategy=strategy)
    second = run_backtest(changed_future, config=config(), strategy=target_strategy)

    assert observed_lengths == [1, 2, 3]
    assert first.trades[0].decision_timestamp == second.trades[0].decision_timestamp
    assert first.trades[0].entry_timestamp == second.trades[0].entry_timestamp
    assert first.trades[0].entry_price == second.trades[0].entry_price


def test_dataset_config_mismatch_fails_closed():
    result = run_backtest((bar(1, version="different"),), config=config(), strategy=lambda history: None)
    assert result.status is BacktestStatus.INVALID
    assert "provider/dataset version" in result.reason
    assert not result.trades


def test_non_valid_bar_fails_whole_run():
    bars = (bar(1), bar(2, quality=ResearchDataQuality.PARTIAL))
    result = run_backtest(bars, config=config(), strategy=target_strategy)
    assert result.status is BacktestStatus.INVALID
    assert "research-ineligible" in result.reason


def test_adjustment_mismatch_fails_closed():
    result = run_backtest((bar(1, adjustment=PriceAdjustment.ADJUSTED),), config=config(), strategy=lambda history: None)
    assert result.status is BacktestStatus.INVALID
    assert "adjustment" in result.reason


def test_run_id_is_deterministic_and_parameters_affect_identity():
    bars = (bar(1), bar(2))
    first = run_backtest(bars, config=config(), strategy=lambda history: None, parameters_json='{"fast": 5, "slow": 10}')
    same = run_backtest(bars, config=config(), strategy=lambda history: None, parameters_json='{"slow":10,"fast":5}')
    different = run_backtest(bars, config=config(), strategy=lambda history: None, parameters_json='{"fast": 6, "slow": 10}')
    assert first.run_id == same.run_id
    assert first.run_id != different.run_id


def test_terminal_open_position_is_marked_unrealized_not_realized():
    bars = (bar(1), bar(2, open="100", high="108", low="98", close="105"))
    result = run_backtest(bars, config=config(), strategy=target_strategy, initial_capital=Decimal("1000"))
    assert not result.trades
    assert result.equity_curve[-1].realized_equity == Decimal("1000")
    assert result.equity_curve[-1].unrealized_pnl > 0
    assert result.equity_curve[-1].equity > result.equity_curve[-1].realized_equity


def test_costs_reduce_net_profit():
    bars = (bar(1), bar(2, open="100", high="112", low="98", close="111"))
    free = run_backtest(bars, config=config(), strategy=target_strategy, initial_capital=Decimal("1000"))
    costs = run_backtest(bars, config=config(commission="0.01", slippage="0.01"), strategy=target_strategy, initial_capital=Decimal("1000"))
    assert costs.trades[0].net_pnl < free.trades[0].net_pnl


def test_zero_trade_run_has_defined_metrics():
    result = run_backtest((bar(1), bar(2)), config=config(), strategy=lambda history: None)
    assert result.metrics.completed_trades == 0
    assert result.metrics.win_rate == Decimal("0")
    assert result.metrics.cumulative_net_return == Decimal("0")



def test_short_position_can_hit_target_and_records_quantity():
    bars = (bar(1), bar(2, open="100", high="102", low="88", close="89"))
    intent = EntryIntent("SHORT", Decimal("90"), Decimal("110"), "short-1")
    result = run_backtest(
        bars,
        config=config(),
        strategy=lambda history: intent if len(history) == 1 else None,
        initial_capital=Decimal("1000"),
    )
    assert result.status is BacktestStatus.COMPLETED
    assert len(result.trades) == 1
    assert result.trades[0].side == "SHORT"
    assert result.trades[0].exit_reason == "TARGET"
    assert result.trades[0].net_pnl == Decimal("100")
    assert result.trades[0].quantity == Decimal("10")
    assert result.metrics.time_in_market_ratio == Decimal("0.5")
