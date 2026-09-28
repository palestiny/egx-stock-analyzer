from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from app.domain.fundamental_analysis.financial_metric import FinancialMetric


class MetricGrowthStatus(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    UNDEFINED = "undefined"


@dataclass(frozen=True)
class MetricGrowthEvidence:
    status: MetricGrowthStatus
    growth: Decimal | None = None


class MetricGrowthAnalyzer:
    """Computes growth only between explicitly comparable financial metrics."""

    @staticmethod
    def analyze(
        current: FinancialMetric,
        previous: FinancialMetric,
    ) -> MetricGrowthEvidence:
        if current.code is not previous.code:
            raise ValueError("financial metrics must have the same metric code")
        if current.scope is not previous.scope:
            raise ValueError("financial metrics must have the same scope")
        if current.currency != previous.currency:
            raise ValueError("financial metrics must use the same currency")
        if current.unit != previous.unit:
            raise ValueError("financial metrics must use the same unit")

        if previous.value == 0:
            return MetricGrowthEvidence(MetricGrowthStatus.UNDEFINED)

        growth = (current.value - previous.value) / previous.value

        if growth > 0:
            status = MetricGrowthStatus.POSITIVE
        elif growth < 0:
            status = MetricGrowthStatus.NEGATIVE
        else:
            status = MetricGrowthStatus.NEUTRAL

        return MetricGrowthEvidence(MetricGrowthStatus(status), growth)
