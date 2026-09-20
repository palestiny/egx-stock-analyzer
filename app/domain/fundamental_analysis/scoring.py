from dataclasses import dataclass

from app.domain.fundamental_analysis.growth import GrowthStatus
from app.domain.fundamental_analysis.liquidity import LiquidityStatus
from app.domain.fundamental_analysis.profitability import ProfitabilityStatus
from app.domain.fundamental_analysis.result import FundamentalAnalysisResult


@dataclass(frozen=True)
class ScoreContribution:
    name: str
    points: int


@dataclass(frozen=True)
class FundamentalScore:
    total: int
    contributions: tuple[ScoreContribution, ...]


class FundamentalScorer:
    @staticmethod
    def score(analysis: FundamentalAnalysisResult) -> FundamentalScore:
        profitability_points = {
            ProfitabilityStatus.PROFITABLE: 1,
            ProfitabilityStatus.NEUTRAL: 0,
            ProfitabilityStatus.UNPROFITABLE: -1,
            ProfitabilityStatus.UNDEFINED: 0,
        }[analysis.profitability.status]

        liquidity_points = {
            LiquidityStatus.ABOVE_ONE: 1,
            LiquidityStatus.EQUAL_TO_ONE: 0,
            LiquidityStatus.BELOW_ONE: -1,
            LiquidityStatus.INSUFFICIENT_DATA: 0,
            LiquidityStatus.UNDEFINED: 0,
        }[analysis.liquidity.status]

        growth_points = {
            GrowthStatus.POSITIVE: 1,
            GrowthStatus.NEUTRAL: 0,
            GrowthStatus.NEGATIVE: -1,
            GrowthStatus.INSUFFICIENT_DATA: 0,
            GrowthStatus.UNDEFINED: 0,
        }[analysis.growth.status]

        contributions = (
            ScoreContribution("profitability", profitability_points),
            ScoreContribution("liquidity", liquidity_points),
            ScoreContribution("growth", growth_points),
        )

        return FundamentalScore(
            total=sum(item.points for item in contributions),
            contributions=contributions,
        )
