from uuid import uuid4

from app.domain.entry_analysis.scoring import EntryQualityScore
from app.domain.opportunity.classification import OpportunityClassification
from app.domain.reporting.alerts import AlertCandidate, AlertGenerator
from app.domain.scoring.stock_quality import StockQualityScore


STOCK_ID = uuid4()


def stock_quality(total_score: int) -> StockQualityScore:
    return StockQualityScore(
        fundamental_score=None,
        technical_score=None,
        total_score=total_score,
    )


def test_buy_classification_produces_alert_candidate():
    candidate = AlertGenerator.generate(
        stock_id=STOCK_ID,
        stock_quality=stock_quality(5),
        entry_quality=EntryQualityScore(1, 1, 2),
        classification=OpportunityClassification.BUY,
    )

    assert candidate == AlertCandidate(
        stock_id=STOCK_ID,
        classification=OpportunityClassification.BUY,
        stock_quality_score=5,
        entry_quality_score=2,
    )


def test_non_buy_classification_produces_no_alert():
    candidate = AlertGenerator.generate(
        stock_id=STOCK_ID,
        stock_quality=stock_quality(2),
        entry_quality=EntryQualityScore(1, 0, 1),
        classification=OpportunityClassification.WATCH,
    )

    assert candidate is None


def test_alert_generation_is_deterministic():
    first = AlertGenerator.generate(
        stock_id=STOCK_ID,
        stock_quality=stock_quality(5),
        entry_quality=EntryQualityScore(1, 1, 2),
        classification=OpportunityClassification.BUY,
    )
    second = AlertGenerator.generate(
        stock_id=STOCK_ID,
        stock_quality=stock_quality(5),
        entry_quality=EntryQualityScore(1, 1, 2),
        classification=OpportunityClassification.BUY,
    )

    assert first == second
