from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.fundamental_analysis.liquidity import (
    LiquidityEvidence,
    LiquidityStatus,
)
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
    liquidity = LiquidityEvidence(
        status=LiquidityStatus.ABOVE_ONE,
        current_ratio=Decimal("2"),
    )

    result = FundamentalAnalysisResult(
        stock_id=stock_id,
        period_end=date(2026, 6, 30),
        profitability=profitability,
        liquidity=liquidity,
    )

    assert result.stock_id == stock_id
    assert result.period_end == date(2026, 6, 30)
    assert result.profitability == profitability
    assert result.liquidity == liquidity


def test_result_is_immutable():
    result = FundamentalAnalysisResult(
        stock_id=uuid4(),
        period_end=date(2026, 6, 30),
        profitability=ProfitabilityEvidence(ProfitabilityStatus.PROFITABLE),
        liquidity=LiquidityEvidence(LiquidityStatus.ABOVE_ONE),
    )

    with pytest.raises((AttributeError, TypeError)):
        result.period_end = date(2026, 7, 1)


def test_result_preserves_independent_evidence_state():
    profitability = ProfitabilityEvidence(ProfitabilityStatus.UNDEFINED)
    liquidity = LiquidityEvidence(LiquidityStatus.INSUFFICIENT_DATA)

    result = FundamentalAnalysisResult(
        stock_id=uuid4(),
        period_end=date(2026, 6, 30),
        profitability=profitability,
        liquidity=liquidity,
    )

    assert result.profitability.status is ProfitabilityStatus.UNDEFINED
    assert result.liquidity.status is LiquidityStatus.INSUFFICIENT_DATA


def test_result_is_deterministic():
    stock_id = uuid4()
    profitability = ProfitabilityEvidence(
        ProfitabilityStatus.PROFITABLE,
        Decimal("0.2"),
    )
    liquidity = LiquidityEvidence(
        LiquidityStatus.ABOVE_ONE,
        Decimal("2"),
    )

    first = FundamentalAnalysisResult(
        stock_id=stock_id,
        period_end=date(2026, 6, 30),
        profitability=profitability,
        liquidity=liquidity,
    )
    second = FundamentalAnalysisResult(
        stock_id=stock_id,
        period_end=date(2026, 6, 30),
        profitability=profitability,
        liquidity=liquidity,
    )

    assert first == second
