from decimal import Decimal

import pytest

from app.domain.portfolio.construction import (
    PortfolioConfiguration,
    PortfolioEvaluator,
    PortfolioPosition,
)


def position(symbol: str, weight: str) -> PortfolioPosition:
    return PortfolioPosition(symbol=symbol, weight=Decimal(weight))


def test_rejects_negative_weights():
    with pytest.raises(ValueError, match="weight"):
        PortfolioPosition(symbol="EGAL", weight=Decimal("-0.1"))


def test_rejects_weights_above_one():
    with pytest.raises(ValueError, match="weight"):
        PortfolioPosition(symbol="EGAL", weight=Decimal("1.1"))


def test_rejects_portfolio_over_allocation():
    with pytest.raises(ValueError, match="weights"):
        PortfolioEvaluator.evaluate(
            [position("EGAL", "0.6"), position("COMI", "0.5")],
            configuration=PortfolioConfiguration(max_single_name_weight=Decimal("0.7")),
            returns={"EGAL": Decimal("0.01"), "COMI": Decimal("0.02")},
        )


def test_enforces_single_name_cap():
    with pytest.raises(ValueError, match="max_single_name_weight"):
        PortfolioEvaluator.evaluate(
            [position("EGAL", "0.6")],
            configuration=PortfolioConfiguration(max_single_name_weight=Decimal("0.5")),
            returns={"EGAL": Decimal("0.01")},
        )


def test_aggregates_multi_symbol_return_deterministically():
    result = PortfolioEvaluator.evaluate(
        [position("EGAL", "0.4"), position("COMI", "0.6")],
        configuration=PortfolioConfiguration(max_single_name_weight=Decimal("0.7")),
        returns={"EGAL": Decimal("0.10"), "COMI": Decimal("-0.05")},
    )
    assert result.snapshot.portfolio_return == Decimal("0.01")
    assert result.snapshot.invested_weight == Decimal("1")
    assert result.snapshot.cash_weight == Decimal("0")


def test_allows_cash_reserve_and_reports_concentration():
    result = PortfolioEvaluator.evaluate(
        [position("EGAL", "0.4"), position("COMI", "0.3")],
        configuration=PortfolioConfiguration(max_single_name_weight=Decimal("0.5")),
        returns={"EGAL": Decimal("0.10"), "COMI": Decimal("0.00")},
    )
    assert result.snapshot.cash_weight == Decimal("0.3")
    assert result.snapshot.concentration_ratio == Decimal("0.4")


def test_rejects_unknown_return_symbol():
    with pytest.raises(ValueError, match="missing"):
        PortfolioEvaluator.evaluate(
            [position("EGAL", "0.5")],
            configuration=PortfolioConfiguration(max_single_name_weight=Decimal("0.6")),
            returns={"COMI": Decimal("0.01")},
        )


def test_empty_portfolio_rejected():
    with pytest.raises(ValueError, match="positions"):
        PortfolioEvaluator.evaluate(
            [],
            configuration=PortfolioConfiguration(max_single_name_weight=Decimal("0.5")),
            returns={},
        )


def test_evaluates_return_series_and_correlation():
    result = PortfolioEvaluator.evaluate_series(
        [position("EGAL", "0.5"), position("COMI", "0.5")],
        configuration=PortfolioConfiguration(max_single_name_weight=Decimal("0.6")),
        returns_by_symbol={
            "EGAL": [Decimal("0.10"), Decimal("-0.05"), Decimal("0.02")],
            "COMI": [Decimal("0.05"), Decimal("-0.02"), Decimal("0.01")],
        },
    )
    assert result.metrics.portfolio_returns == (
        Decimal("0.075"), Decimal("-0.035"), Decimal("0.015")
    )
    assert result.metrics.max_drawdown > Decimal("0")
    assert result.metrics.volatility > Decimal("0")
    assert result.metrics.average_pairwise_correlation > Decimal("0.9")


def test_series_requires_equal_lengths_and_known_symbols():
    with pytest.raises(ValueError, match="same length"):
        PortfolioEvaluator.evaluate_series(
            [position("EGAL", "0.5"), position("COMI", "0.5")],
            configuration=PortfolioConfiguration(max_single_name_weight=Decimal("0.6")),
            returns_by_symbol={
                "EGAL": [Decimal("0.01")],
                "COMI": [Decimal("0.01"), Decimal("0.02")],
            },
        )
