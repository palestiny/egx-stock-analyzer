from dataclasses import dataclass
from datetime import date

from app.domain.fundamental_analysis.financial_period import FinancialPeriod


@dataclass(frozen=True)
class HistoricalFinancialSnapshot:
    """A financial period with an explicit point-in-time availability boundary."""

    period: FinancialPeriod
    available_at: date

    def __post_init__(self) -> None:
        if self.available_at < self.period.period_end:
            raise ValueError(
                "available_at cannot be earlier than the financial period end"
            )

    def is_available_at(self, decision_date: date) -> bool:
        return self.available_at <= decision_date

    def to_financial_period(self) -> FinancialPeriod:
        return self.period
