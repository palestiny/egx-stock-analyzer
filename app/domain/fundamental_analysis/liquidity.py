from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from app.domain.fundamental_analysis.financial_period import FinancialPeriod


class LiquidityStatus(Enum):
    ABOVE_ONE = "above_one"
    BELOW_ONE = "below_one"
    EQUAL_TO_ONE = "equal_to_one"
    INSUFFICIENT_DATA = "insufficient_data"
    UNDEFINED = "undefined"


@dataclass(frozen=True)
class LiquidityEvidence:
    status: LiquidityStatus
    current_ratio: Decimal | None = None


class CurrentRatioAnalyzer:
    @staticmethod
    def analyze(period: FinancialPeriod) -> LiquidityEvidence:
        if period.current_assets is None or period.current_liabilities is None:
            return LiquidityEvidence(LiquidityStatus.INSUFFICIENT_DATA)

        if period.current_liabilities == 0:
            return LiquidityEvidence(LiquidityStatus.UNDEFINED)

        current_ratio = period.current_assets / period.current_liabilities

        if current_ratio > 1:
            status = LiquidityStatus.ABOVE_ONE
        elif current_ratio < 1:
            status = LiquidityStatus.BELOW_ONE
        else:
            status = LiquidityStatus.EQUAL_TO_ONE

        return LiquidityEvidence(
            status=status,
            current_ratio=current_ratio,
        )
