from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.fundamental_analysis.growth import GrowthEvidence, GrowthStatus
from app.domain.fundamental_analysis.liquidity import (
    LiquidityEvidence,
    LiquidityStatus,
)
from app.domain.fundamental_analysis.orchestrator import FundamentalAnalysisOrchestrator
from app.domain.fundamental_analysis.profitability import (
    ProfitabilityEvidence,
    ProfitabilityStatus,
)
from app.domain.fundamental_analysis.result import FundamentalAnalysisResult


def create_period(revenue="1000", period_end=date(2026, 6, 30)) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=period_end,
        revenue=Decimal(revenue),
        net_income=Decimal("200"),
        current_assets=Decimal("200"),
        current_liabilities=Decimal("100"),
    )


def test_orchestrator_composes_fundamental_evidence():
    stock_id = uuid4()
    current = create_period()
    previous = create_period("800", date(2025, 6, 30))
    profitability = ProfitabilityEvidence(ProfitabilityStatus.PROFITABLE, Decimal("0.2"))
    liquidity = LiquidityEvidence(LiquidityStatus.ABOVE_ONE, Decimal("2"))
    growth = GrowthEvidence(GrowthStatus.POSITIVE, Decimal("0.25"))

    with patch(
        "app.domain.fundamental_analysis.orchestrator.NetProfitMarginAnalyzer.analyze",
        return_value=profitability,
    ) as profitability_analyze, patch(
        "app.domain.fundamental_analysis.orchestrator.CurrentRatioAnalyzer.analyze",
        return_value=liquidity,
    ) as liquidity_analyze, patch(
        "app.domain.fundamental_analysis.orchestrator.RevenueGrowthAnalyzer.analyze",
        return_value=growth,
    ) as growth_analyze:
        result = FundamentalAnalysisOrchestrator.analyze(
            stock_id,
            current,
            previous,
        )

    profitability_analyze.assert_called_once_with(current)
    liquidity_analyze.assert_called_once_with(current)
    growth_analyze.assert_called_once_with(current, previous)
    assert isinstance(result, FundamentalAnalysisResult)
    assert result.stock_id == stock_id
    assert result.profitability == profitability
    assert result.liquidity == liquidity
    assert result.growth == growth


def test_orchestrator_passes_periods_to_analyzers():
    current = create_period()
    previous = create_period("800", date(2025, 6, 30))

    with patch(
        "app.domain.fundamental_analysis.orchestrator.NetProfitMarginAnalyzer.analyze",
        return_value=ProfitabilityEvidence(ProfitabilityStatus.PROFITABLE),
    ) as profitability_analyze, patch(
        "app.domain.fundamental_analysis.orchestrator.CurrentRatioAnalyzer.analyze",
        return_value=LiquidityEvidence(LiquidityStatus.ABOVE_ONE),
    ) as liquidity_analyze, patch(
        "app.domain.fundamental_analysis.orchestrator.RevenueGrowthAnalyzer.analyze",
        return_value=GrowthEvidence(GrowthStatus.POSITIVE),
    ) as growth_analyze:
        FundamentalAnalysisOrchestrator.analyze(uuid4(), current, previous)

    profitability_analyze.assert_called_once_with(current)
    liquidity_analyze.assert_called_once_with(current)
    growth_analyze.assert_called_once_with(current, previous)


def test_orchestrator_is_deterministic():
    stock_id = uuid4()
    current = create_period()
    previous = create_period("800", date(2025, 6, 30))

    first = FundamentalAnalysisOrchestrator.analyze(stock_id, current, previous)
    second = FundamentalAnalysisOrchestrator.analyze(stock_id, current, previous)

    assert first == second
