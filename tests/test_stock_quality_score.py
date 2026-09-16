import pytest

from app.domain.fundamental_analysis.scoring import FundamentalScore, ScoreContribution
from app.domain.technical_analysis.scoring import TechnicalScore
from app.domain.scoring.stock_quality import StockQualityScorer


def fundamental_score(total: int) -> FundamentalScore:
    return FundamentalScore(
        total=total,
        contributions=(ScoreContribution("test", total),),
    )


def technical_score(total: int) -> TechnicalScore:
    return TechnicalScore(
        trend_points=total,
        momentum_points=0,
        volume_points=0,
        total_score=total,
    )


def test_maximum_scores_produce_six():
    result = StockQualityScorer.score(
        fundamental_score(3),
        technical_score(3),
    )

    assert result.total_score == 6


def test_minimum_scores_produce_negative_six():
    result = StockQualityScorer.score(
        fundamental_score(-3),
        technical_score(-3),
    )

    assert result.total_score == -6


def test_mixed_scores_are_summed():
    result = StockQualityScorer.score(
        fundamental_score(2),
        technical_score(-1),
    )

    assert result.total_score == 1


def test_zero_component_scores_produce_zero():
    result = StockQualityScorer.score(
        fundamental_score(0),
        technical_score(0),
    )

    assert result.total_score == 0


def test_result_is_immutable():
    result = StockQualityScorer.score(
        fundamental_score(1),
        technical_score(2),
    )

    with pytest.raises(AttributeError):
        result.total_score = 10


def test_scoring_is_deterministic():
    fundamental = fundamental_score(2)
    technical = technical_score(1)

    first = StockQualityScorer.score(fundamental, technical)
    second = StockQualityScorer.score(fundamental, technical)

    assert first == second


def test_component_scores_are_preserved():
    fundamental = fundamental_score(2)
    technical = technical_score(-1)

    result = StockQualityScorer.score(fundamental, technical)

    assert result.fundamental_score == fundamental
    assert result.technical_score == technical
