from collections.abc import Iterable
from datetime import date

from app.application.analysis.run_stock_analysis import RunStockAnalysis
from app.application.stocks.catalog import StockCatalog
from app.domain.execution import Execution


class InvalidMarketUniverseError(ValueError):
    """Raised when the requested market universe is invalid."""


class RunMarketAnalysis:
    def __init__(
        self,
        stock_catalog: StockCatalog,
        run_stock_analysis: RunStockAnalysis,
    ) -> None:
        self._stock_catalog = stock_catalog
        self._run_stock_analysis = run_stock_analysis

    def execute(self, symbols: Iterable[str], as_of: date) -> Execution:
        normalized_symbols = self._normalize_symbols(symbols)

        execution = Execution.create()
        execution.start()

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
                execution.record_stock_failure(symbol, reason=str(error))
            else:
                execution.record_stock_success(symbol)

        execution.finish()
        return execution

    @staticmethod
    def _normalize_symbols(symbols: Iterable[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for raw_symbol in symbols:
            symbol = raw_symbol.strip().upper()
            if not symbol:
                raise InvalidMarketUniverseError(
                    "Market universe cannot contain an empty stock symbol"
                )
            if symbol in seen:
                raise InvalidMarketUniverseError(
                    f"Duplicate stock symbol in market universe: {symbol}"
                )
            seen.add(symbol)
            normalized.append(symbol)

        return normalized
