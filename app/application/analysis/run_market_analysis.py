from dataclasses import dataclass
from datetime import date
from collections.abc import Iterable

from app.application.analysis.run_stock_analysis_by_symbol import (
    RunStockAnalysisBySymbol,
)
from app.domain.execution import Execution


class DuplicateStockSymbolError(ValueError):
    """Raised when a market-wide request contains duplicate stock symbols."""


@dataclass(frozen=True)
class MarketAnalysisResult:
    execution: Execution


class RunMarketAnalysis:
    """Orchestrates the existing single-stock analysis capability over a universe."""

    def __init__(self, run_stock_analysis_by_symbol: RunStockAnalysisBySymbol) -> None:
        self._run_stock_analysis_by_symbol = run_stock_analysis_by_symbol

    def execute(self, symbols: Iterable[str], as_of: date) -> MarketAnalysisResult:
        normalized_symbols = [symbol.strip().upper() for symbol in symbols]

        if len(normalized_symbols) != len(set(normalized_symbols)):
            raise DuplicateStockSymbolError(
                "Market analysis universe cannot contain duplicate stock symbols"
            )

        execution = Execution.create()
        execution.start()

        if not normalized_symbols:
            execution.complete()
            return MarketAnalysisResult(execution=execution)

        for symbol in normalized_symbols:
            try:
                self._run_stock_analysis_by_symbol.execute(symbol, as_of)
            except Exception as exc:
                execution.record_stock_failure(symbol, str(exc))
            else:
                execution.record_stock_success(symbol)

        execution.finish()
        return MarketAnalysisResult(execution=execution)
