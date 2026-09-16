from datetime import date
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch

from app.domain.fundamental_analysis.financial_period import FinancialPeriod
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
    )


def test_orchestrator_composes_profitability_evidence():
    stock_id = uuid4()
    profitability = ProfitabilityEvidence(
        status=ProfitabilityStatus.PROFITABLE,
        net_profit_margin=Decimal("0.2"),
    )

    with patch(
        "app.domain.fundamental_analysis.orchestrator.NetProfitMarginAnalyzer.analyze",
        return_value=profitability,
    ) as analyze:
        result = FundamentalAnalysisOrchestrator.analyze(
            stock_id,
            create_period(),
        )

    analyze.assert_called_once()
    assert isinstance(result, FundamentalAnalysisResult)
    assert result.stock_id == stock_id
    assert result.period_end == date(2026, 6, 30)
    assert result.profitability == profitability


def test_orchestrator_passes_financial_period_to_analyzer():
    period = create_period()

    with patch(
        "app.domain.fundamental_analysis.orchestrator.NetProfitMarginAnalyzer.analyze",
        return_value=ProfitabilityEvidence(ProfitabilityStatus.PROFITABLE),
    ) as analyze:
        FundamentalAnalysisOrchestrator.analyze(uuid4(), period)

    analyze.assert_called_once_with(period)


def test_orchestrator_is_deterministic():
    stock_id = uuid4()
    period = create_period()

    first = FundamentalAnalysisOrchestrator.analyze(stock_id, period)
    second = FundamentalAnalysisOrchestrator.analyze(stock_id, period)

    assert first == second
