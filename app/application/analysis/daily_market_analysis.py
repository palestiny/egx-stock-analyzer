from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.application.analysis.result_store import (
    AnalysisResultPersistenceError,
    AnalysisResultStore,
)
from app.application.analysis.stock_analysis import StockAnalysisPipeline, StockAnalysisResult
from app.application.execution.orchestrator import ExecutionOrchestrator
from app.application.execution.retry import RetryPolicy
from app.domain.execution import Execution
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
    execution: Execution
    stock_results: dict[str, StockAnalysisResult]


class DailyMarketAnalysis:
    def __init__(
        self,
        retry_policy: RetryPolicy,
        result_store: AnalysisResultStore | None = None,
    ) -> None:
        self._orchestrator = ExecutionOrchestrator(
            retry_policy,
            propagate_exceptions=(AnalysisResultPersistenceError,),
        )
        self._result_store = result_store

    def run(
        self,
        inputs: list[StockAnalysisInput],
        analysis_date: date | None = None,
        analysis_run_id: UUID | None = None,
    ) -> DailyMarketAnalysisResult:
        stock_results: dict[str, StockAnalysisResult] = {}
        inputs_by_symbol = {item.symbol: item for item in inputs}

        def analyze_stock(symbol: str) -> None:
            request = inputs_by_symbol[symbol]
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
            if self._result_store is not None:
                self._result_store.save(
                    symbol,
                    result,
                    analysis_date,
                    analysis_run_id=analysis_run_id,
                )

        execution = self._orchestrator.run(
            [item.symbol for item in inputs],
            analyze_stock,
        )

        return DailyMarketAnalysisResult(
            execution=execution,
            stock_results=stock_results,
        )
