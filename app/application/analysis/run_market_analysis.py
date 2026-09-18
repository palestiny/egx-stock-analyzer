from datetime import date

from app.application.stocks.catalog import StockCatalog
from app.application.analysis.run_stock_analysis import RunStockAnalysis
from app.domain.execution import Execution
from app.domain.stocks.stock import Stock


class RunMarketAnalysis:
    """Execute the existing single-stock analysis capability across a requested universe."""

    def __init__(
        self,
        stock_catalog: StockCatalog,
        run_stock_analysis: RunStockAnalysis,
    ) -> None:
        self._stock_catalog = stock_catalog
        self._run_stock_analysis = run_stock_analysis

    def execute(self, symbols: list[str], as_of: date) -> Execution:
        normalized_symbols = [symbol.strip().upper() for symbol in symbols]

        if len(normalized_symbols) != len(set(normalized_symbols)):
            raise ValueError("Duplicate stock symbol in market analysis universe")

        execution = Execution.create()
        execution.start()

        if not normalized_symbols:
            execution.complete()
            return execution

        for symbol in normalized_symbols:
            stock = self._stock_catalog.get(symbol)

            if stock is None:
                execution.record_stock_failure(
                    symbol,
                    f"Unknown stock symbol: {symbol}",
                )
                continue

            try:
                self._run_stock_analysis.execute(stock, as_of)
            except Exception as exc:
                reason = str(exc) or exc.__class__.__name__
                execution.record_stock_failure(stock.symbol, reason)
            else:
                execution.record_stock_success(stock.symbol)

        execution.finish()
        return execution
