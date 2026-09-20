from uuid import UUID

from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.fundamental_analysis.growth import RevenueGrowthAnalyzer
from app.domain.fundamental_analysis.liquidity import CurrentRatioAnalyzer
from app.domain.fundamental_analysis.profitability import NetProfitMarginAnalyzer
from app.domain.fundamental_analysis.result import FundamentalAnalysisResult


class FundamentalAnalysisOrchestrator:
    @staticmethod
    def analyze(
        stock_id: UUID,
        current_period: FinancialPeriod,
        previous_period: FinancialPeriod,
    ) -> FundamentalAnalysisResult:
        profitability = NetProfitMarginAnalyzer.analyze(current_period)
        liquidity = CurrentRatioAnalyzer.analyze(current_period)
        growth = RevenueGrowthAnalyzer.analyze(
            current_period,
            previous_period,
        )

        return FundamentalAnalysisResult(
            stock_id=stock_id,
            period_end=current_period.period_end,
            profitability=profitability,
            liquidity=liquidity,
            growth=growth,
        )
