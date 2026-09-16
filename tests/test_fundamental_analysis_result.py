from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.fundamental_analysis.growth import GrowthEvidence, GrowthStatus
from app.domain.fundamental_analysis.liquidity import (
    LiquidityEvidence,
    LiquidityStatus,
)
from app.domain.fundamental_analysis.profitability import (
    ProfitabilityEvidence,
    ProfitabilityStatus,
)
from app.domain.fundamental_analysis.result import FundamentalAnalysisResult


def create_evidence():
    return (
        ProfitabilityEvidence(ProfitabilityStatus.PROFITABLE, Decimal("0.2")),
        LiquidityEvidence(LiquidityStatus.ABOVE_ONE, Decimal("2")),
        GrowthEvidence(GrowthStatus.POSITIVE, Decimal("0.2")),
    )


def test_result_composes_fundamental_evidence():
    stock_id = uuid4()
    profitability, liquidity, growth = create_evidence()

    result = FundamentalAnalysisResult(
        stock_id=stock_id,
        period_end=date(2026, 6, 30),
        profitability=profitability,
        liquidity=liquidity,
        growth=growth,
    )

    assert result.stock_id == stock_id
    assert result.period_end == date(2026, 6, 30)
    assert result.profitability == profitability
    assert result.liquidity == liquidity
    assert result.growth == growth


def test_result_is_immutable():
    profitability, liquidity, growth = create_evidence()
    result = FundamentalAnalysisResult(
        stock_id=uuid4(),
        period_end=date(2026, 6, 30),
        profitability=profitability,
        liquidity=liquidity,
        growth=growth,
    )

    with pytest.raises((AttributeError, TypeError)):
        result.period_end = date(2026, 7, 1)


def test_result_preserves_independent_evidence_state():
    profitability = ProfitabilityEvidence(ProfitabilityStatus.UNDEFINED)
    liquidity = LiquidityEvidence(LiquidityStatus.INSUFFICIENT_DATA)
    growth = GrowthEvidence(GrowthStatus.UNDEFINED)

    result = FundamentalAnalysisResult(
        stock_id=uuid4(),
        period_end=date(2026, 6, 30),
        profitability=profitability,
        liquidity=liquidity,
        growth=growth,
    )

    assert result.profitability.status is ProfitabilityStatus.UNDEFINED
    assert result.liquidity.status is LiquidityStatus.INSUFFICIENT_DATA
    assert result.growth.status is GrowthStatus.UNDEFINED


def test_result_is_deterministic():
    stock_id = uuid4()
    profitability, liquidity, growth = create_evidence()

    first = FundamentalAnalysisResult(
        stock_id=stock_id,
        period_end=date(2026, 6, 30),
        profitability=profitability,
        liquidity=liquidity,
        growth=growth,
    )
    second = FundamentalAnalysisResult(
        stock_id=stock_id,
        period_end=date(2026, 6, 30),
        profitability=profitability,
        liquidity=liquidity,
        growth=growth,
    )

    assert first == second
