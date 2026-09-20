from dataclasses import dataclass

from app.domain.fundamental_analysis.scoring import FundamentalScore
from app.domain.technical_analysis.scoring import TechnicalScore


@dataclass(frozen=True)
class StockQualityScore:
    fundamental_score: FundamentalScore
    technical_score: TechnicalScore
    total_score: int


class StockQualityScorer:
    @staticmethod
    def score(
        fundamental_score: FundamentalScore,
        technical_score: TechnicalScore,
    ) -> StockQualityScore:
        return StockQualityScore(
            fundamental_score=fundamental_score,
            technical_score=technical_score,
            total_score=fundamental_score.total + technical_score.total_score,
        )
