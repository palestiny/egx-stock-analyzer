from datetime import date
from decimal import Decimal

import pytest

from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.fundamental_analysis.growth import (
    GrowthEvidence,
    GrowthStatus,
    NetIncomeGrowthAnalyzer,
)


def create_period(net_income: str, period_end: date) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=period_end,
        revenue=Decimal("1000"),
        net_income=Decimal(net_income),
    )


def test_positive_net_income_growth():
    previous = create_period("100", date(2025, 6, 30))
    current = create_period("150", date(2026, 6, 30))
    result = NetIncomeGrowthAnalyzer.analyze(current, previous)
    assert result.status is GrowthStatus.POSITIVE
    assert result.net_income_growth == Decimal("0.5")


def test_negative_net_income_growth():
    previous = create_period("100", date(2025, 6, 30))
    current = create_period("50", date(2026, 6, 30))
    result = NetIncomeGrowthAnalyzer.analyze(current, previous)
    assert result.status is GrowthStatus.NEGATIVE
    assert result.net_income_growth == Decimal("-0.5")


def test_neutral_net_income_growth():
    previous = create_period("100", date(2025, 6, 30))
    current = create_period("100", date(2026, 6, 30))
    result = NetIncomeGrowthAnalyzer.analyze(current, previous)
    assert result.status is GrowthStatus.NEUTRAL
    assert result.net_income_growth == Decimal("0")


def test_zero_previous_net_income_is_undefined():
    previous = create_period("0", date(2025, 6, 30))
    current = create_period("100", date(2026, 6, 30))
    result = NetIncomeGrowthAnalyzer.analyze(current, previous)
    assert result.status is GrowthStatus.UNDEFINED
    assert result.net_income_growth is None


def test_growth_evidence_is_immutable():
    evidence = GrowthEvidence(
        status=GrowthStatus.POSITIVE,
        net_income_growth=Decimal("0.5"),
    )
    with pytest.raises((AttributeError, TypeError)):
        evidence.status = GrowthStatus.NEGATIVE


def test_net_income_growth_is_deterministic():
    previous = create_period("100", date(2025, 6, 30))
    current = create_period("150", date(2026, 6, 30))
    first = NetIncomeGrowthAnalyzer.analyze(current, previous)
    second = NetIncomeGrowthAnalyzer.analyze(current, previous)
    assert first == second
