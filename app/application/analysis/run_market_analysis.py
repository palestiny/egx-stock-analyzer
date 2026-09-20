from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from app.application.analysis.result_store import AnalysisResultStore, AnalysisResultPersistenceError
from app.application.analysis.run_stock_analysis import RunStockAnalysis
from app.application.stocks.catalog import StockCatalog
from app.domain.execution import Execution


class DuplicateMarketAnalysisSymbolError(ValueError):
    """Raised when a market analysis universe contains duplicate symbols."""


@dataclass(frozen=True)
class MarketAnalysisResult:
    execution: Execution


class RunMarketAnalysis:
    def __init__(
        self,
        stock_catalog: StockCatalog,
        run_stock_analysis: RunStockAnalysis,
        result_store: AnalysisResultStore,
    ) -> None:
        self._stock_catalog = stock_catalog
        self._run_stock_analysis = run_stock_analysis
        self._result_store = result_store

    def execute(
        self,
        symbols: Sequence[str],
        as_of: date,
    ) -> MarketAnalysisResult:
        normalized_symbols = self._normalize_symbols(symbols)

        execution = Execution.create()
        execution.start()
        analysis_run_id = uuid4()
        self._result_store.create_analysis_run(analysis_run_id, as_of)

        if not normalized_symbols:
            execution.complete()
            self._result_store.update_analysis_run_state(
                analysis_run_id,
                execution.state,
            )
            return MarketAnalysisResult(execution=execution)

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
                    analysis_run_id=analysis_run_id,
                )
            except AnalysisResultPersistenceError:
                raise
            except Exception as error:
                execution.record_stock_failure(stock.symbol, reason=str(error))
            else:
                execution.record_stock_success(stock.symbol)

        execution.finish()
        self._result_store.update_analysis_run_state(
            analysis_run_id,
            execution.state,
        )
        return MarketAnalysisResult(execution=execution)

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
