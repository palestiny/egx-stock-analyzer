from datetime import date
from decimal import Decimal

import pytest

from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.fundamental_analysis.growth import (
    RevenueGrowthAnalyzer,
    GrowthEvidence,
    GrowthStatus,
)


def create_period(revenue: str, period_end: date) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=period_end,
        revenue=Decimal(revenue),
        net_income=Decimal("100"),
    )


def test_positive_revenue_growth():
    previous = create_period("1000", date(2025, 6, 30))
    current = create_period("1200", date(2026, 6, 30))

    result = RevenueGrowthAnalyzer.analyze(current, previous)

    assert result.status is GrowthStatus.POSITIVE
    assert result.revenue_growth == Decimal("0.2")


def test_negative_revenue_growth():
    previous = create_period("1000", date(2025, 6, 30))
    current = create_period("800", date(2026, 6, 30))

    result = RevenueGrowthAnalyzer.analyze(current, previous)

    assert result.status is GrowthStatus.NEGATIVE
    assert result.revenue_growth == Decimal("-0.2")


def test_neutral_revenue_growth():
    previous = create_period("1000", date(2025, 6, 30))
    current = create_period("1000", date(2026, 6, 30))

    result = RevenueGrowthAnalyzer.analyze(current, previous)

    assert result.status is GrowthStatus.NEUTRAL
    assert result.revenue_growth == Decimal("0")


def test_zero_previous_revenue_is_undefined():
    previous = create_period("0", date(2025, 6, 30))
    current = create_period("1000", date(2026, 6, 30))

    result = RevenueGrowthAnalyzer.analyze(current, previous)

    assert result.status is GrowthStatus.UNDEFINED
    assert result.revenue_growth is None


def test_growth_evidence_is_immutable():
    evidence = GrowthEvidence(
        status=GrowthStatus.POSITIVE,
        revenue_growth=Decimal("0.2"),
    )

    with pytest.raises((AttributeError, TypeError)):
        evidence.status = GrowthStatus.NEGATIVE


def test_growth_analysis_is_deterministic():
    previous = create_period("1000", date(2025, 6, 30))
    current = create_period("1200", date(2026, 6, 30))

    first = RevenueGrowthAnalyzer.analyze(current, previous)
    second = RevenueGrowthAnalyzer.analyze(current, previous)

    assert first == second
