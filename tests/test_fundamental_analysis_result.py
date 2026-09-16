from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.fundamental_analysis.profitability import (
    ProfitabilityEvidence,
    ProfitabilityStatus,
)
from app.domain.fundamental_analysis.result import FundamentalAnalysisResult


def test_result_composes_fundamental_evidence():
    stock_id = uuid4()
    profitability = ProfitabilityEvidence(
        status=ProfitabilityStatus.PROFITABLE,
        net_profit_margin=Decimal("0.2"),
    )

    result = FundamentalAnalysisResult(
        stock_id=stock_id,
        period_end=date(2026, 6, 30),
        profitability=profitability,
    )

    assert result.stock_id == stock_id
    assert result.period_end == date(2026, 6, 30)
    assert result.profitability == profitability


def test_result_is_immutable():
    result = FundamentalAnalysisResult(
        stock_id=uuid4(),
        period_end=date(2026, 6, 30),
        profitability=ProfitabilityEvidence(
            status=ProfitabilityStatus.PROFITABLE,
            net_profit_margin=Decimal("0.2"),
        ),
    )

    with pytest.raises((AttributeError, TypeError)):
        result.period_end = date(2026, 7, 1)


def test_result_preserves_independent_evidence_state():
    profitability = ProfitabilityEvidence(
        status=ProfitabilityStatus.UNDEFINED,
    )

    result = FundamentalAnalysisResult(
        stock_id=uuid4(),
        period_end=date(2026, 6, 30),
        profitability=profitability,
    )

    assert result.profitability.status is ProfitabilityStatus.UNDEFINED
    assert result.profitability.net_profit_margin is None


def test_result_is_deterministic():
    stock_id = uuid4()
    profitability = ProfitabilityEvidence(
        status=ProfitabilityStatus.PROFITABLE,
        net_profit_margin=Decimal("0.2"),
    )

    first = FundamentalAnalysisResult(
        stock_id=stock_id,
        period_end=date(2026, 6, 30),
        profitability=profitability,
    )
    second = FundamentalAnalysisResult(
        stock_id=stock_id,
        period_end=date(2026, 6, 30),
        profitability=profitability,
    )

    assert first == second
