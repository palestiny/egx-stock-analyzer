from uuid import uuid4

from app.domain.entry_analysis.scoring import EntryQualityScore
from app.domain.fundamental_analysis.scoring import FundamentalScore
from app.domain.opportunity.classification import OpportunityClassification
from app.domain.reporting.alerts import AlertCandidate, AlertGenerator
from app.domain.scoring.stock_quality import StockQualityScore
from app.domain.technical_analysis.scoring import TechnicalScore


STOCK_ID = uuid4()


def stock_quality(total_score: int) -> StockQualityScore:
    fundamental_score = FundamentalScore(total=0, contributions=())
    technical_score = TechnicalScore(
        trend_points=0,
        momentum_points=0,
        volume_points=0,
        total_score=0,
    )

    return StockQualityScore(
        fundamental_score=fundamental_score,
        technical_score=technical_score,
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
