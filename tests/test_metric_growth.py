from decimal import Decimal

import pytest

from app.domain.fundamental_analysis.financial_metric import (
    FinancialMetric,
    FinancialMetricCode,
    FinancialMetricScope,
)
from app.domain.fundamental_analysis.metric_growth import MetricGrowthAnalyzer, MetricGrowthStatus


def metric(code: FinancialMetricCode, value: str, *, currency: str = "EGP", unit: str = "million") -> FinancialMetric:
    return FinancialMetric(
        code=code,
        source_label=code.value,
        scope=FinancialMetricScope.CONSOLIDATED,
        currency=currency,
        unit=unit,
        value=Decimal(value),
    )


def test_growth_uses_declared_metric_identity():
    current = metric(FinancialMetricCode.NET_OPERATING_INCOME, "120")
    previous = metric(FinancialMetricCode.NET_OPERATING_INCOME, "100")

    evidence = MetricGrowthAnalyzer.analyze(current, previous)

    assert evidence.status is MetricGrowthStatus.POSITIVE
    assert evidence.growth == Decimal("0.2")


def test_net_operating_income_is_not_comparable_to_revenue():
    current = metric(FinancialMetricCode.NET_OPERATING_INCOME, "120")
    previous = metric(FinancialMetricCode.REVENUE, "100")

    with pytest.raises(ValueError, match="metric code"):
        MetricGrowthAnalyzer.analyze(current, previous)


def test_different_currency_is_not_comparable():
    current = metric(FinancialMetricCode.NET_PROFIT, "120")
    previous = metric(FinancialMetricCode.NET_PROFIT, "100", currency="USD")

    with pytest.raises(ValueError, match="currency"):
        MetricGrowthAnalyzer.analyze(current, previous)


def test_different_scope_is_not_comparable():
    current = metric(FinancialMetricCode.NET_PROFIT, "120")
    previous = FinancialMetric(
        code=FinancialMetricCode.NET_PROFIT,
        source_label="net_profit",
        scope=FinancialMetricScope.STANDALONE,
        currency="EGP",
        unit="million",
        value=Decimal("100"),
    )

    with pytest.raises(ValueError, match="scope"):
        MetricGrowthAnalyzer.analyze(current, previous)
