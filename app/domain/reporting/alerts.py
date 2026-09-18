from dataclasses import dataclass
from uuid import UUID

from app.domain.entry_analysis.scoring import EntryQualityScore
from app.domain.opportunity.classification import OpportunityClassification
from app.domain.scoring.stock_quality import StockQualityScore


@dataclass(frozen=True)
class AlertCandidate:
    stock_id: UUID
    snapshot_id: UUID | None
    classification: OpportunityClassification
    stock_quality_score: int
    entry_quality_score: int


class AlertGenerator:
    @staticmethod
    def generate(
        stock_id: UUID,
        snapshot_id: UUID | None = None,
        stock_quality: StockQualityScore,
        entry_quality: EntryQualityScore,
        classification: OpportunityClassification,
    ) -> AlertCandidate | None:
        if classification is not OpportunityClassification.BUY:
            return None

        return AlertCandidate(
            stock_id=stock_id,
            snapshot_id=snapshot_id,
            classification=classification,
            stock_quality_score=stock_quality.total_score,
            entry_quality_score=entry_quality.total_score,
        )
