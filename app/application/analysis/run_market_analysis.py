from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

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
    ) -> None:
        self._stock_catalog = stock_catalog
        self._run_stock_analysis = run_stock_analysis

    def execute(
        self,
        symbols: Sequence[str],
        as_of: date,
    ) -> MarketAnalysisResult:
        normalized_symbols = self._normalize_symbols(symbols)

        execution = Execution.create()
        execution.start()

        if not normalized_symbols:
            execution.complete()
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
                self._run_stock_analysis.execute(stock, as_of)
            except Exception as error:
                execution.record_stock_failure(stock.symbol, reason=str(error))
            else:
                execution.record_stock_success(stock.symbol)

        execution.finish()
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
