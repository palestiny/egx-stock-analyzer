from decimal import Decimal

import pytest

from app.domain.backtesting.risk_metrics import BacktestRiskMetrics


def test_risk_metrics_calculate_drawdown_profit_factor_and_sharpe():
    metrics = BacktestRiskMetrics.calculate(
        [Decimal("0.10"), Decimal("-0.05"), Decimal("0.02"), Decimal("-0.03")],
        periods_per_year=252,
    )

    assert metrics.trade_count == 4
    assert metrics.total_return == Decimal("1.10") * Decimal("0.95") * Decimal("1.02") * Decimal("0.97") - 1
    assert metrics.max_drawdown > Decimal("0")
    assert metrics.profit_factor > Decimal("1")
    assert metrics.sharpe_ratio is not None
    assert metrics.win_rate == Decimal("0.5")


def test_risk_metrics_calculate_var_and_cvar_at_five_percent():
    metrics = BacktestRiskMetrics.calculate(
        [
            Decimal("0.10"),
            Decimal("0.02"),
            Decimal("-0.01"),
            Decimal("-0.04"),
            Decimal("-0.20"),
        ],
        periods_per_year=1,
    )

    assert metrics.var_95 is not None
    assert metrics.cvar_95 is not None
    assert metrics.cvar_95 <= metrics.var_95


def test_empty_returns_are_rejected():
    with pytest.raises(ValueError, match="returns"):
        BacktestRiskMetrics.calculate([], periods_per_year=252)


def test_invalid_periods_per_year_are_rejected():
    with pytest.raises(ValueError, match="periods_per_year"):
        BacktestRiskMetrics.calculate([Decimal("0.01")], periods_per_year=0)
