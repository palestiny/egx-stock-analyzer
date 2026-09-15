from datetime import date
from decimal import Decimal

import pytest

from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.fundamental_analysis.profitability import (
    NetProfitMarginAnalyzer,
    ProfitabilityStatus,
)


def period(revenue: str, net_income: str) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=date(2026, 6, 30),
        revenue=Decimal(revenue),
        net_income=Decimal(net_income),
    )


def test_positive_net_profit_margin():
    evidence = NetProfitMarginAnalyzer.analyze(period("1000", "200"))

    assert evidence.status is ProfitabilityStatus.PROFITABLE
    assert evidence.net_profit_margin == Decimal("0.2")


def test_negative_net_profit_margin():
    evidence = NetProfitMarginAnalyzer.analyze(period("1000", "-100"))

    assert evidence.status is ProfitabilityStatus.UNPROFITABLE
    assert evidence.net_profit_margin == Decimal("-0.1")


def test_zero_net_profit_margin():
    evidence = NetProfitMarginAnalyzer.analyze(period("1000", "0"))

    assert evidence.status is ProfitabilityStatus.NEUTRAL
    assert evidence.net_profit_margin == Decimal("0")


def test_zero_revenue_is_undefined():
    evidence = NetProfitMarginAnalyzer.analyze(period("0", "100"))

    assert evidence.status is ProfitabilityStatus.UNDEFINED
    assert evidence.net_profit_margin is None


def test_evidence_is_immutable():
    evidence = NetProfitMarginAnalyzer.analyze(period("1000", "200"))

    with pytest.raises((AttributeError, TypeError)):
        evidence.status = ProfitabilityStatus.NEUTRAL


def test_analysis_is_deterministic():
    data = period("1000", "200")

    first = NetProfitMarginAnalyzer.analyze(data)
    second = NetProfitMarginAnalyzer.analyze(data)

    assert first == second
