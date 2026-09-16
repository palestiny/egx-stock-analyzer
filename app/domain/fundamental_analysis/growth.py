from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from app.domain.fundamental_analysis.financial_period import FinancialPeriod


class GrowthStatus(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    INSUFFICIENT_DATA = "insufficient_data"
    UNDEFINED = "undefined"


@dataclass(frozen=True)
class GrowthEvidence:
    status: GrowthStatus
    revenue_growth: Decimal | None = None


class RevenueGrowthAnalyzer:
    @staticmethod
    def analyze(
        current_period: FinancialPeriod,
        previous_period: FinancialPeriod,
    ) -> GrowthEvidence:
        previous_revenue = previous_period.revenue

        if previous_revenue == 0:
            return GrowthEvidence(GrowthStatus.UNDEFINED)

        revenue_growth = (
            (current_period.revenue - previous_revenue)
            / previous_revenue
        )

        if revenue_growth > 0:
            status = GrowthStatus.POSITIVE
        elif revenue_growth < 0:
            status = GrowthStatus.NEGATIVE
        else:
            status = GrowthStatus.NEUTRAL

        return GrowthEvidence(
            status=status,
            revenue_growth=revenue_growth,
        )
