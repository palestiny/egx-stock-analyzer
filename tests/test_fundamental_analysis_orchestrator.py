from datetime import date
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch

from app.domain.fundamental_analysis.financial_period import FinancialPeriod
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


def create_period() -> FinancialPeriod:
    return FinancialPeriod(
        period_end=date(2026, 6, 30),
        revenue=Decimal("1000"),
        net_income=Decimal("200"),
        current_assets=Decimal("200"),
        current_liabilities=Decimal("100"),
    )


def test_orchestrator_composes_fundamental_evidence():
    stock_id = uuid4()
    profitability = ProfitabilityEvidence(ProfitabilityStatus.PROFITABLE, Decimal("0.2"))
    liquidity = LiquidityEvidence(LiquidityStatus.ABOVE_ONE, Decimal("2"))

    with patch(
        "app.domain.fundamental_analysis.orchestrator.NetProfitMarginAnalyzer.analyze",
        return_value=profitability,
    ) as profitability_analyze, patch(
        "app.domain.fundamental_analysis.orchestrator.CurrentRatioAnalyzer.analyze",
        return_value=liquidity,
    ) as liquidity_analyze:
        result = FundamentalAnalysisOrchestrator.analyze(stock_id, create_period())

    profitability_analyze.assert_called_once()
    liquidity_analyze.assert_called_once()
    assert isinstance(result, FundamentalAnalysisResult)
    assert result.stock_id == stock_id
    assert result.profitability == profitability
    assert result.liquidity == liquidity


def test_orchestrator_passes_financial_period_to_analyzers():
    period = create_period()

    with patch(
        "app.domain.fundamental_analysis.orchestrator.NetProfitMarginAnalyzer.analyze",
        return_value=ProfitabilityEvidence(ProfitabilityStatus.PROFITABLE),
    ) as profitability_analyze, patch(
        "app.domain.fundamental_analysis.orchestrator.CurrentRatioAnalyzer.analyze",
        return_value=LiquidityEvidence(LiquidityStatus.ABOVE_ONE),
    ) as liquidity_analyze:
        FundamentalAnalysisOrchestrator.analyze(uuid4(), period)

    profitability_analyze.assert_called_once_with(period)
    liquidity_analyze.assert_called_once_with(period)


def test_orchestrator_is_deterministic():
    stock_id = uuid4()
    period = create_period()

    first = FundamentalAnalysisOrchestrator.analyze(stock_id, period)
    second = FundamentalAnalysisOrchestrator.analyze(stock_id, period)

    assert first == second
