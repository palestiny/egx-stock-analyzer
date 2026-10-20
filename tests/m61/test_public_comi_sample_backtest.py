from tools.m61_public_comi_sample_backtest import run_sample_backtest


def test_public_comi_history_runs_production_strategy_deterministically() -> None:
    first = run_sample_backtest()
    second = run_sample_backtest()

    assert first == second
    assert first["source"] == (
        "M-Abdelmegeed/Project-EGX, "
        "EGX Stock data/COMI Historical Data.csv"
    )
    assert first["valid_market_rows"] > 600
    assert first["evaluation_bars"] > 150
    assert first["warmup_bars"] >= 252
    assert first["rejected_rows"] == []
    assert first["completed_trades"] >= 0
    assert "cumulative_net_trade_return" in first
    assert "not independently verified" in first["source_rights"]
    assert "not for investment decisions" in first["interpretation"]
