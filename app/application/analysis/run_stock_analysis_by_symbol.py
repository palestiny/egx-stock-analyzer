from datetime import date

from app.application.analysis.run_stock_analysis import RunStockAnalysis
from app.application.stocks.catalog import StockCatalog


class UnknownStockSymbolError(ValueError):
    """Raised when a requested symbol is not present in the stock catalog."""


class RunStockAnalysisBySymbol:
    def __init__(
        self,
        stock_catalog: StockCatalog,
        run_stock_analysis: RunStockAnalysis,
    ) -> None:
        self._stock_catalog = stock_catalog
        self._run_stock_analysis = run_stock_analysis

    def execute(self, symbol: str, as_of: date) -> None:
        stock = self._stock_catalog.get(symbol)
        if stock is None:
            raise UnknownStockSymbolError(f"Unknown stock symbol: {symbol}")
        self._run_stock_analysis.execute(stock, as_of)
