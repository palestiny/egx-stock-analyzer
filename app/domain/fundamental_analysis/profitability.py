from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from app.domain.fundamental_analysis.financial_period import FinancialPeriod


class ProfitabilityStatus(Enum):
    PROFITABLE = "profitable"
    UNPROFITABLE = "unprofitable"
    NEUTRAL = "neutral"
    UNDEFINED = "undefined"


@dataclass(frozen=True)
class ProfitabilityEvidence:
    status: ProfitabilityStatus
    net_profit_margin: Decimal | None = None


class NetProfitMarginAnalyzer:
    @staticmethod
    def analyze(period: FinancialPeriod) -> ProfitabilityEvidence:
        if period.revenue == 0:
            return ProfitabilityEvidence(
                status=ProfitabilityStatus.UNDEFINED,
            )

        net_profit_margin = period.net_income / period.revenue

        if net_profit_margin > 0:
            status = ProfitabilityStatus.PROFITABLE
        elif net_profit_margin < 0:
            status = ProfitabilityStatus.UNPROFITABLE
        else:
            status = ProfitabilityStatus.NEUTRAL

        return ProfitabilityEvidence(
            status=status,
            net_profit_margin=net_profit_margin,
        )
