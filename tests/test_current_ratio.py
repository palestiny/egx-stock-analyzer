from datetime import date
from decimal import Decimal

import pytest

from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.fundamental_analysis.liquidity import (
    CurrentRatioAnalyzer,
    LiquidityStatus,
)


def period(current_assets: str, current_liabilities: str) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=date(2026, 6, 30),
        revenue=Decimal("1000"),
        net_income=Decimal("200"),
        current_assets=Decimal(current_assets),
        current_liabilities=Decimal(current_liabilities),
    )


def test_current_ratio_above_one():
    evidence = CurrentRatioAnalyzer.analyze(period("200", "100"))
    assert evidence.status is LiquidityStatus.ABOVE_ONE
    assert evidence.current_ratio == Decimal("2")


def test_current_ratio_below_one():
    evidence = CurrentRatioAnalyzer.analyze(period("50", "100"))
    assert evidence.status is LiquidityStatus.BELOW_ONE
    assert evidence.current_ratio == Decimal("0.5")


def test_current_ratio_equal_one():
    evidence = CurrentRatioAnalyzer.analyze(period("100", "100"))
    assert evidence.status is LiquidityStatus.EQUAL_TO_ONE
    assert evidence.current_ratio == Decimal("1")


def test_zero_current_liabilities_is_undefined():
    evidence = CurrentRatioAnalyzer.analyze(period("100", "0"))
    assert evidence.status is LiquidityStatus.UNDEFINED
    assert evidence.current_ratio is None


def test_missing_current_ratio_data_is_insufficient():
    data = FinancialPeriod(
        period_end=date(2026, 6, 30),
        revenue=Decimal("1000"),
        net_income=Decimal("200"),
    )
    evidence = CurrentRatioAnalyzer.analyze(data)
    assert evidence.status is LiquidityStatus.INSUFFICIENT_DATA
    assert evidence.current_ratio is None


def test_evidence_is_immutable():
    evidence = CurrentRatioAnalyzer.analyze(period("200", "100"))
    with pytest.raises((AttributeError, TypeError)):
        evidence.status = LiquidityStatus.BELOW_ONE


def test_analysis_is_deterministic():
    data = period("200", "100")
    assert CurrentRatioAnalyzer.analyze(data) == CurrentRatioAnalyzer.analyze(data)
