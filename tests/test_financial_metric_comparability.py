from decimal import Decimal

from app.domain.fundamental_analysis.financial_metric import (
    FinancialMetric,
    FinancialMetricCode,
    FinancialMetricScope,
 )
from app.domain.fundamental_analysis.financial_metric_comparability import (
    FinancialMetricComparabilityStatus,
    StrategyV0FinancialMetricSelector,
 )

def metric(code: FinancialMetricCode) -> FinancialMetric:
    return FinancialMetric(
        code=code,
        source_label=code.value,
        scope=FinancialMetricScope.CONSOLIDATED,
        currency="EGP",
        unit="million",
        value=Decimal("100"),
    )

def test_generic_revenue_is_explicitly_accepted_as_strategy_v0_comparable():
    result = StrategyV0FinancialMetricSelector.select(
        metric(FinancialMetricCode.REVENUE)
    )
    assert result.status is FinancialMetricComparabilityStatus.COMPARABLE
    assert result.metric is not None
    assert result.metric.code is FinancialMetricCode.REVENUE

def test_net_operating_income_is_not_silently_substituted_for_revenue():
    result = StrategyV0FinancialMetricSelector.select(
        metric(FinancialMetricCode.NET_OPERATING_INCOME)
    )
    assert result.status is FinancialMetricComparabilityStatus.UNSUPPORTED
    assert result.metric is None
    assert "net_operating_income" in result.reason

def test_net_interest_income_is_not_silently_substituted_for_revenue():
    result = StrategyV0FinancialMetricSelector.select(
        metric(FinancialMetricCode.NET_INTEREST_INCOME)
    )
    assert result.status is FinancialMetricComparabilityStatus.UNSUPPORTED
    assert result.metric is None

def test_net_profit_is_not_used_as_revenue_growth_metric():
    result = StrategyV0FinancialMetricSelector.select(
        metric(FinancialMetricCode.NET_PROFIT)
    )
    assert result.status is FinancialMetricComparabilityStatus.UNSUPPORTED
    assert result.metric is None
