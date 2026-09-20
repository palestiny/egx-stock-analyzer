from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.application.analysis.run_stock_analysis import RunStockAnalysis
from app.application.analysis.run_store import AnalysisRunStore
from app.domain.analysis_run import AnalysisRun
from app.application.stocks.catalog import StockCatalog
from app.domain.execution import Execution


class DuplicateMarketAnalysisSymbolError(ValueError):
    """Raised when a market analysis universe contains duplicate symbols."""


@dataclass(frozen=True)
class MarketAnalysisResult:
    execution: Execution
    analysis_run_id: UUID


class RunMarketAnalysis:
    def __init__(
        self,
        stock_catalog: StockCatalog,
        run_stock_analysis: RunStockAnalysis,
        analysis_run_store: AnalysisRunStore,
    ) -> None:
        self._stock_catalog = stock_catalog
        self._run_stock_analysis = run_stock_analysis
        self._analysis_run_store = analysis_run_store

    def execute(
        self,
        symbols: Sequence[str],
        as_of: date,
    ) -> MarketAnalysisResult:
        normalized_symbols = self._normalize_symbols(symbols)

        execution = Execution.create()
        execution.start()
        analysis_run = AnalysisRun.create().with_state(execution.state)
        self._analysis_run_store.save(analysis_run)

        if not normalized_symbols:
            execution.complete()
            completed_run = analysis_run.with_state(execution.state)
            self._analysis_run_store.save(completed_run)
            return MarketAnalysisResult(execution=execution, analysis_run_id=analysis_run.id)

        for symbol in normalized_symbols:
            stock = self._stock_catalog.get(symbol)

            if stock is None:
                execution.record_stock_failure(
                    symbol,
                    reason=f"Unknown stock symbol: {symbol}",
                )
                continue

            try:
                self._run_stock_analysis.execute(
                    stock,
                    as_of,
                    analysis_run_id=analysis_run.id,
                )
            except Exception as error:
                execution.record_stock_failure(stock.symbol, reason=str(error))
            else:
                execution.record_stock_success(stock.symbol)

        execution.finish()
        self._analysis_run_store.save(analysis_run.with_state(execution.state))
        return MarketAnalysisResult(execution=execution, analysis_run_id=analysis_run.id)

    @staticmethod
    def _normalize_symbols(symbols: Sequence[str]) -> list[str]:
        normalized_symbols = [symbol.strip().upper() for symbol in symbols]
        seen: set[str] = set()

        for symbol in normalized_symbols:
            if not symbol:
                raise ValueError("Stock symbol cannot be empty")
            if symbol in seen:
                raise DuplicateMarketAnalysisSymbolError(
                    f"Duplicate stock symbol: {symbol}"
                )
            seen.add(symbol)

        return normalized_symbols
