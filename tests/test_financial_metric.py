from decimal import Decimal

import pytest

from app.domain.fundamental_analysis.financial_metric import (
    FinancialMetric,
    FinancialMetricCode,
    FinancialMetricScope,
)


def test_financial_metric_retains_source_identity_and_accounting_boundary():
    metric = FinancialMetric(
        code=FinancialMetricCode.NET_OPERATING_INCOME,
        source_label="Net Operating Income",
        scope=FinancialMetricScope.CONSOLIDATED,
        currency="EGP",
        unit="million",
        value=Decimal("98956"),
    )

    assert metric.code is FinancialMetricCode.NET_OPERATING_INCOME
    assert metric.source_label == "Net Operating Income"
    assert metric.scope is FinancialMetricScope.CONSOLIDATED
    assert metric.currency == "EGP"
    assert metric.unit == "million"
    assert metric.value == Decimal("98956")


def test_financial_metric_rejects_empty_source_label():
    with pytest.raises(ValueError, match="source_label"):
        FinancialMetric(
            code=FinancialMetricCode.NET_PROFIT,
            source_label="",
            scope=FinancialMetricScope.CONSOLIDATED,
            currency="EGP",
            unit="million",
            value=Decimal("55196"),
        )


def test_net_operating_income_is_not_relabelled_as_revenue():
    metric = FinancialMetric(
        code=FinancialMetricCode.NET_OPERATING_INCOME,
        source_label="Net Operating Income",
        scope=FinancialMetricScope.CONSOLIDATED,
        currency="EGP",
        unit="million",
        value=Decimal("98956"),
    )

    assert metric.code is not FinancialMetricCode.REVENUE


def test_financial_metric_rejects_empty_currency_or_unit():
    with pytest.raises(ValueError, match="currency"):
        FinancialMetric(
            code=FinancialMetricCode.NET_PROFIT,
            source_label="Net Profit",
            scope=FinancialMetricScope.CONSOLIDATED,
            currency="",
            unit="million",
            value=Decimal("55196"),
        )

    with pytest.raises(ValueError, match="unit"):
        FinancialMetric(
            code=FinancialMetricCode.NET_PROFIT,
            source_label="Net Profit",
            scope=FinancialMetricScope.CONSOLIDATED,
            currency="EGP",
            unit="",
            value=Decimal("55196"),
        )
