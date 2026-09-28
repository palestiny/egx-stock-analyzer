from dataclasses import dataclass
from enum import Enum

from app.domain.fundamental_analysis.financial_metric import (
    FinancialMetric,
    FinancialMetricCode,
 )

class FinancialMetricComparabilityStatus(Enum):
    COMPARABLE = "comparable"
    UNSUPPORTED = "unsupported"

@dataclass(frozen=True)
class FinancialMetricComparability:
    status: FinancialMetricComparabilityStatus
    metric: FinancialMetric | None = None
    reason: str | None = None

class StrategyV0FinancialMetricSelector:
    """Selects only metrics whose semantic identity is explicitly accepted."""

    @staticmethod
    def select(metric: FinancialMetric) -> FinancialMetricComparability:
        if metric.code is FinancialMetricCode.REVENUE:
            return FinancialMetricComparability(
                status=FinancialMetricComparabilityStatus.COMPARABLE,
                metric=metric,
            )

        return FinancialMetricComparability(
            status=FinancialMetricComparabilityStatus.UNSUPPORTED,
            reason=(
                f"Metric '{metric.code.value}' is not accepted as the "
                "Strategy v0 comparable growth metric"
            ),
        )
