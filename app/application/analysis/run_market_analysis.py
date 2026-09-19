from dataclasses import dataclass
from datetime import date

from app.application.analysis.run_stock_analysis import RunStockAnalysis
from app.application.analysis.run_stock_analysis_by_symbol import RunStockAnalysisBySymbol
from app.application.execution.orchestrator import ExecutionOrchestrator
from app.application.execution.retry import RetryPolicy
from app.application.stocks.catalog import StockCatalog
from app.domain.execution import Execution


@dataclass(frozen=True)
class RunMarketAnalysisResult:
    execution: Execution


class RunMarketAnalysis:
    def __init__(
        self,
        stock_catalog: StockCatalog,
        run_stock_analysis: RunStockAnalysis,
        retry_policy: RetryPolicy,
    ) -> None:
        self._stock_catalog = stock_catalog
        self._run_stock_analysis_by_symbol = RunStockAnalysisBySymbol(
            stock_catalog=stock_catalog,
            run_stock_analysis=run_stock_analysis,
        )
        self._orchestrator = ExecutionOrchestrator(
            retry_policy,
        )

    def execute(self, symbols: list[str], as_of: date) -> RunMarketAnalysisResult:
        normalized_symbols = [symbol.strip().upper() for symbol in symbols]
        if any(not symbol for symbol in normalized_symbols):
            raise ValueError("Stock symbol cannot be empty")

        if len(normalized_symbols) != len(set(normalized_symbols)):
            raise ValueError("Duplicate stock symbol in market analysis universe")

        execution = self._orchestrator.run(
            normalized_symbols,
            lambda symbol: self._run_stock_analysis_by_symbol.execute(symbol, as_of),
        )
        return RunMarketAnalysisResult(execution=execution)
