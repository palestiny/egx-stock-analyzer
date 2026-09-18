from dataclasses import dataclass
from uuid import UUID

from app.domain.reporting.alerts import AlertCandidate


@dataclass(frozen=True)
class AlertCandidateResponse:
    stock_id: UUID
    classification: str
    stock_quality_score: int
    entry_quality_score: int

    @classmethod
    def from_candidate(cls, candidate: AlertCandidate) -> "AlertCandidateResponse":
        return cls(
            stock_id=candidate.stock_id,
            classification=candidate.classification.value,
            stock_quality_score=candidate.stock_quality_score,
            entry_quality_score=candidate.entry_quality_score,
        )
