from dataclasses import dataclass
from uuid import UUID

from app.application.analysis.stock_analysis import StockAnalysisPipeline, StockAnalysisResult
from app.application.execution.orchestrator import ExecutionOrchestrator
from app.application.execution.retry import RetryPolicy
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe


@dataclass(frozen=True)
class StockAnalysisInput:
    symbol: str
    stock_id: UUID
    timeframe: Timeframe
    price_bars: list[PriceBar]
    current_period: FinancialPeriod
    previous_period: FinancialPeriod
    momentum_lookback: int
    volume_lookback: int


@dataclass(frozen=True)
class DailyMarketAnalysisResult:
    execution: object
    stock_results: dict[str, StockAnalysisResult]


class DailyMarketAnalysis:
    def __init__(self, retry_policy: RetryPolicy) -> None:
        self._orchestrator = ExecutionOrchestrator(retry_policy)

    def run(self, inputs: list[StockAnalysisInput]) -> DailyMarketAnalysisResult:
        stock_results: dict[str, StockAnalysisResult] = {}

        def analyze_stock(symbol: str) -> None:
            request = next(item for item in inputs if item.symbol == symbol)
            result = StockAnalysisPipeline.analyze(
                request.stock_id,
                request.timeframe,
                request.price_bars,
                request.current_period,
                request.previous_period,
                request.momentum_lookback,
                request.volume_lookback,
            )
            stock_results[symbol] = result

        execution = self._orchestrator.run(
            [item.symbol for item in inputs],
            analyze_stock,
        )

        return DailyMarketAnalysisResult(
            execution=execution,
            stock_results=stock_results,
        )
