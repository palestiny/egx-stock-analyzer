from dataclasses import dataclass
from enum import Enum

from app.domain.entry_analysis.scoring import EntryQualityScore
from app.domain.scoring.stock_quality import StockQualityScore


class OpportunityClassification(Enum):
    BUY = "buy"
    WATCH = "watch"
    HOLD = "hold"
    AVOID = "avoid"


@dataclass(frozen=True)
class OpportunityClassificationResult:
    classification: OpportunityClassification


class OpportunityClassifier:
    @staticmethod
    def classify(
        stock_quality: StockQualityScore,
        entry_quality: EntryQualityScore,
    ) -> OpportunityClassificationResult:
        stock_score = stock_quality.total_score
        entry_score = entry_quality.total_score

        if stock_score <= -2:
            classification = OpportunityClassification.AVOID
        elif stock_score >= 4 and entry_score >= 1:
            classification = OpportunityClassification.BUY
        elif stock_score >= 2:
            classification = OpportunityClassification.WATCH
        else:
            classification = OpportunityClassification.HOLD

        return OpportunityClassificationResult(
            classification=classification,
        )
