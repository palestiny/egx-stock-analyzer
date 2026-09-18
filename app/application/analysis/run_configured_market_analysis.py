from datetime import date

from app.application.analysis.run_market_analysis import RunMarketAnalysis
from app.application.stocks.catalog import StockCatalog
from app.domain.execution import Execution


class RunConfiguredMarketAnalysis:
    def __init__(
        self,
        stock_catalog: StockCatalog,
        run_market_analysis: RunMarketAnalysis,
    ) -> None:
        self._stock_catalog = stock_catalog
        self._run_market_analysis = run_market_analysis

    def execute(self, as_of: date) -> Execution:
        symbols = list(self._stock_catalog.symbols())
        return self._run_market_analysis.execute(symbols, as_of)
