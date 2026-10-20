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



def test_public_comi_report_includes_historical_risk_profile() -> None:
    report = run_sample_backtest()
    risk = report["historical_risk_profile"]

    assert risk["status"] == "completed"
    assert risk["bars"] == report["valid_market_rows"]
    assert risk["daily_returns"] == risk["bars"] - 1
    assert float(risk["maximum_close_to_close_drawdown"]) <= 0
    assert float(risk["annualized_realized_volatility"]) >= 0
    assert risk["worst_daily_return"]["date"]
    assert risk["worst_overnight_gap"]["date"]
    assert risk["sessions_with_volume_at_least_1_5x_prior_20_session_average"] >= 0
    assert any("not a market-wide crash score" in note for note in risk["method_notes"])
