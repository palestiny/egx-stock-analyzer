from uuid import UUID

from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.fundamental_analysis.liquidity import CurrentRatioAnalyzer
from app.domain.fundamental_analysis.profitability import NetProfitMarginAnalyzer
from app.domain.fundamental_analysis.result import FundamentalAnalysisResult


class FundamentalAnalysisOrchestrator:
    @staticmethod
    def analyze(
        stock_id: UUID,
        period: FinancialPeriod,
    ) -> FundamentalAnalysisResult:
        profitability = NetProfitMarginAnalyzer.analyze(period)
        liquidity = CurrentRatioAnalyzer.analyze(period)

        return FundamentalAnalysisResult(
            stock_id=stock_id,
            period_end=period.period_end,
            profitability=profitability,
            liquidity=liquidity,
        )
