from decimal import Decimal
from uuid import uuid4
from datetime import date

import pytest

from app.domain.fundamental_analysis.growth import GrowthEvidence, GrowthStatus
from app.domain.fundamental_analysis.liquidity import LiquidityEvidence, LiquidityStatus
from app.domain.fundamental_analysis.profitability import (
    ProfitabilityEvidence,
    ProfitabilityStatus,
)
from app.domain.fundamental_analysis.result import FundamentalAnalysisResult
from app.domain.fundamental_analysis.scoring import FundamentalScorer


def create_result(
    profitability_status: ProfitabilityStatus,
    liquidity_status: LiquidityStatus,
    growth_status: GrowthStatus,
) -> FundamentalAnalysisResult:
    return FundamentalAnalysisResult(
        stock_id=uuid4(),
        period_end=date(2026, 6, 30),
        profitability=ProfitabilityEvidence(
            status=profitability_status,
            net_profit_margin=Decimal("0.2")
            if profitability_status is not ProfitabilityStatus.UNDEFINED
            else None,
        ),
        liquidity=LiquidityEvidence(
            status=liquidity_status,
            current_ratio=Decimal("2")
            if liquidity_status is not LiquidityStatus.UNDEFINED
            else None,
        ),
        growth=GrowthEvidence(
            status=growth_status,
            revenue_growth=Decimal("0.2")
            if growth_status is not GrowthStatus.UNDEFINED
            else None,
        ),
    )


def test_all_positive_evidence_produces_plus_three():
    result = FundamentalScorer.score(
        create_result(
            ProfitabilityStatus.PROFITABLE,
            LiquidityStatus.ABOVE_ONE,
            GrowthStatus.POSITIVE,
        )
    )

    assert result.total == 3
    assert [item.points for item in result.contributions] == [1, 1, 1]


def test_all_neutral_evidence_produces_zero():
    result = FundamentalScorer.score(
        create_result(
            ProfitabilityStatus.NEUTRAL,
            LiquidityStatus.EQUAL_TO_ONE,
            GrowthStatus.NEUTRAL,
        )
    )

    assert result.total == 0
    assert [item.points for item in result.contributions] == [0, 0, 0]


def test_all_negative_evidence_produces_minus_three():
    result = FundamentalScorer.score(
        create_result(
            ProfitabilityStatus.UNPROFITABLE,
            LiquidityStatus.BELOW_ONE,
            GrowthStatus.NEGATIVE,
        )
    )

    assert result.total == -3
    assert [item.points for item in result.contributions] == [-1, -1, -1]


def test_undefined_and_insufficient_evidence_contribute_zero():
    result = FundamentalScorer.score(
        create_result(
            ProfitabilityStatus.UNDEFINED,
            LiquidityStatus.INSUFFICIENT_DATA,
            GrowthStatus.UNDEFINED,
        )
    )

    assert result.total == 0
    assert [item.points for item in result.contributions] == [0, 0, 0]


def test_score_preserves_explainable_contributions():
    result = FundamentalScorer.score(
        create_result(
            ProfitabilityStatus.PROFITABLE,
            LiquidityStatus.BELOW_ONE,
            GrowthStatus.POSITIVE,
        )
    )

    assert [item.name for item in result.contributions] == [
        "profitability",
        "liquidity",
        "growth",
    ]
    assert [item.points for item in result.contributions] == [1, -1, 1]


def test_score_is_immutable():
    result = FundamentalScorer.score(
        create_result(
            ProfitabilityStatus.PROFITABLE,
            LiquidityStatus.ABOVE_ONE,
            GrowthStatus.POSITIVE,
        )
    )

    with pytest.raises((AttributeError, TypeError)):
        result.total = 0


def test_score_is_deterministic():
    analysis = create_result(
        ProfitabilityStatus.PROFITABLE,
        LiquidityStatus.ABOVE_ONE,
        GrowthStatus.POSITIVE,
    )

    first = FundamentalScorer.score(analysis)
    second = FundamentalScorer.score(analysis)

    assert first == second
