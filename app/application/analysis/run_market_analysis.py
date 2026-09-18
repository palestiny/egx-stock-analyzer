from dataclasses import dataclass
from datetime import date

from app.application.analysis.run_stock_analysis import RunStockAnalysis
from app.application.stocks.catalog import StockCatalog
from app.domain.execution import Execution


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
        symbols: list[str],
        as_of: date,
    ) -> MarketAnalysisResult:
        normalized_symbols = [symbol.strip().upper() for symbol in symbols]

        if len(normalized_symbols) != len(set(normalized_symbols)):
            raise ValueError("Duplicate stock symbol in market analysis universe")

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
                execution.record_stock_failure(symbol, reason=str(error))
            else:
                execution.record_stock_success(symbol)

        execution.finish()
        return MarketAnalysisResult(execution=execution)
