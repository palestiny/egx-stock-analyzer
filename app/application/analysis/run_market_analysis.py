from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.application.analysis.run_stock_analysis_by_symbol import RunStockAnalysisBySymbol
from app.application.execution.orchestrator import ExecutionOrchestrator
from app.application.execution.retry import RetryPolicy
from app.domain.execution import Execution


class DuplicateMarketAnalysisSymbolError(ValueError):
    """Raised when a market analysis universe contains duplicate symbols."""


@dataclass(frozen=True)
class MarketAnalysisResult:
    execution: Execution


class RunMarketAnalysis:
    def __init__(
        self,
        run_stock_analysis_by_symbol: RunStockAnalysisBySymbol,
        retry_policy: RetryPolicy,
    ) -> None:
        self._run_stock_analysis_by_symbol = run_stock_analysis_by_symbol
        self._orchestrator = ExecutionOrchestrator(retry_policy)

    def execute(
        self,
        symbols: Sequence[str],
        as_of: date,
    ) -> MarketAnalysisResult:
        normalized_symbols = self._normalize_symbols(symbols)

        execution = self._orchestrator.run(
            normalized_symbols,
            lambda symbol: self._run_stock_analysis_by_symbol.execute(symbol, as_of),
        )
        return MarketAnalysisResult(execution=execution)

    @staticmethod
    def _normalize_symbols(symbols: Sequence[str]) -> list[str]:
        normalized_symbols = [symbol.strip().upper() for symbol in symbols]
        seen: set[str] = set()

        for symbol in normalized_symbols:
            if symbol in seen:
                raise DuplicateMarketAnalysisSymbolError(
                    f"Duplicate stock symbol: {symbol}"
                )
            seen.add(symbol)

        return normalized_symbols
