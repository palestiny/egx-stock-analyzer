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
        raise NotImplementedError
