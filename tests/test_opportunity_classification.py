from app.domain.entry_analysis.scoring import EntryQualityScore
from app.domain.scoring.stock_quality import StockQualityScore
from app.domain.opportunity.classification import (
    OpportunityClassification,
    OpportunityClassifier,
)
from app.domain.fundamental_analysis.scoring import FundamentalScore
from app.domain.technical_analysis.scoring import TechnicalScore


def stock_quality(total: int) -> StockQualityScore:
    fundamental = FundamentalScore(total=0, contributions=())
    technical = TechnicalScore(
        trend_points=0,
        momentum_points=0,
        volume_points=0,
        total_score=0,
    )
    return StockQualityScore(
        fundamental_score=fundamental,
        technical_score=technical,
        total_score=total,
    )


def entry_quality(total: int) -> EntryQualityScore:
    return EntryQualityScore(
        support_points=1 if total >= 1 else 0,
        resistance_points=1 if total >= 2 else 0,
        total_score=total,
    )


def test_strong_quality_and_favorable_entry_produces_buy():
    result = OpportunityClassifier.classify(
        stock_quality(4),
        entry_quality(1),
    )

    assert result.classification is OpportunityClassification.BUY


def test_strong_quality_without_entry_context_produces_watch():
    result = OpportunityClassifier.classify(
        stock_quality(4),
        entry_quality(0),
    )

    assert result.classification is OpportunityClassification.WATCH


def test_positive_quality_with_favorable_entry_produces_watch():
    result = OpportunityClassifier.classify(
        stock_quality(2),
        entry_quality(1),
    )

    assert result.classification is OpportunityClassification.WATCH


def test_positive_quality_without_entry_context_produces_watch():
    result = OpportunityClassifier.classify(
        stock_quality(2),
        entry_quality(0),
    )

    assert result.classification is OpportunityClassification.WATCH


def test_neutral_combination_produces_hold():
    result = OpportunityClassifier.classify(
        stock_quality(0),
        entry_quality(0),
    )

    assert result.classification is OpportunityClassification.HOLD


def test_negative_but_not_avoid_quality_produces_hold():
    result = OpportunityClassifier.classify(
        stock_quality(-1),
        entry_quality(2),
    )

    assert result.classification is OpportunityClassification.HOLD


def test_sufficiently_negative_quality_produces_avoid():
    result = OpportunityClassifier.classify(
        stock_quality(-2),
        entry_quality(2),
    )

    assert result.classification is OpportunityClassification.AVOID


def test_result_is_immutable():
    result = OpportunityClassifier.classify(
        stock_quality(4),
        entry_quality(1),
    )

    try:
        result.classification = OpportunityClassification.HOLD
    except AttributeError:
        pass
    else:
        raise AssertionError("Opportunity classification result must be immutable")


def test_classification_is_deterministic():
    quality = stock_quality(3)
    entry = entry_quality(1)

    first = OpportunityClassifier.classify(quality, entry)
    second = OpportunityClassifier.classify(quality, entry)

    assert first == second
