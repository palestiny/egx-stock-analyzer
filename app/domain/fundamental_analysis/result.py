from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.domain.fundamental_analysis.liquidity import LiquidityEvidence
from app.domain.fundamental_analysis.profitability import ProfitabilityEvidence


@dataclass(frozen=True)
class FundamentalAnalysisResult:
    stock_id: UUID
    period_end: date
    profitability: ProfitabilityEvidence
    liquidity: LiquidityEvidence
