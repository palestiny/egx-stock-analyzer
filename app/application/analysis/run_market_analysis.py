from dataclasses import dataclass
from datetime import date

from app.application.analysis.run_stock_analysis_by_symbol import (
    RunStockAnalysisBySymbol,
)
from app.domain.execution import Execution


@dataclass(frozen=True)
class MarketAnalysisResult:
    execution: Execution


class RunMarketAnalysis:
    def __init__(
        self,
        run_stock_analysis_by_symbol: RunStockAnalysisBySymbol,
    ) -> None:
        self._run_stock_analysis_by_symbol = run_stock_analysis_by_symbol

    def execute(self, symbols: list[str], as_of: date) -> MarketAnalysisResult:
        normalized_symbols = [symbol.strip().upper() for symbol in symbols]

        if len(normalized_symbols) != len(set(normalized_symbols)):
            raise ValueError("Market analysis universe contains duplicate symbols")

        execution = Execution.create()
        execution.start()

        for symbol in normalized_symbols:
            try:
                self._run_stock_analysis_by_symbol.execute(symbol, as_of)
            except Exception as error:
                execution.record_stock_failure(symbol, reason=str(error))
            else:
                execution.record_stock_success(symbol)

        execution.finish()
        return MarketAnalysisResult(execution=execution)
