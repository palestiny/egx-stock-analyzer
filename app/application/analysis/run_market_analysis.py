from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.application.analysis.run_stock_analysis import RunStockAnalysis
from app.application.analysis.run_store import AnalysisRunStore
from app.domain.analysis_run import AnalysisRun, AnalysisRunOutcome
from app.application.stocks.catalog import StockCatalog
from app.domain.execution import Execution


class DuplicateMarketAnalysisSymbolError(ValueError):
    """Raised when a market analysis universe contains duplicate symbols."""


@dataclass(frozen=True)
class MarketAnalysisResult:
    execution: Execution
    analysis_run_id: UUID


class RunMarketAnalysis:
    def __init__(
        self,
        stock_catalog: StockCatalog,
        run_stock_analysis: RunStockAnalysis,
        analysis_run_store: AnalysisRunStore | None = None,
    ) -> None:
        self._stock_catalog = stock_catalog
        self._run_stock_analysis = run_stock_analysis
        if analysis_run_store is None:
            from app.application.analysis.run_store import InMemoryAnalysisRunStore

            analysis_run_store = InMemoryAnalysisRunStore()
        self._analysis_run_store = analysis_run_store

    def execute(
        self,
        symbols: Sequence[str],
        as_of: date,
        owner_user_id: UUID | None = None,
    ) -> MarketAnalysisResult:
        normalized_symbols = self._normalize_symbols(symbols)

        execution = Execution.create()
        execution.start()
        analysis_run = AnalysisRun.create(owner_user_id=owner_user_id).with_state(execution.state)
        self._analysis_run_store.save(analysis_run)

        outcomes: list[AnalysisRunOutcome] = []

        if not normalized_symbols:
            execution.complete()
            completed_run = analysis_run.with_state(execution.state)
            self._analysis_run_store.save(completed_run)
            return MarketAnalysisResult(
                execution=execution,
                analysis_run_id=analysis_run.id,
            )

        for symbol in normalized_symbols:
            stock = self._stock_catalog.get(symbol)

            if stock is None:
                execution.record_stock_failure(
                    symbol,
                    reason=f"Unknown stock symbol: {symbol}",
                )
                outcomes.append(
                    AnalysisRunOutcome.failed(
                        symbol,
                        "UNKNOWN_SYMBOL",
                        symbol,
                    )
                )
            else:
                try:
                    if owner_user_id is None:
                        self._run_stock_analysis.execute(
                            stock,
                            as_of,
                            analysis_run_id=analysis_run.id,
                        )
                    else:
                        self._run_stock_analysis.execute(
                            stock,
                            as_of,
                            analysis_run_id=analysis_run.id,
                            owner_user_id=owner_user_id,
                        )
                except Exception as error:
                    execution.record_stock_failure(
                        stock.symbol,
                        reason=str(error),
                    )
                    outcomes.append(
                        AnalysisRunOutcome.failed(
                            stock.symbol,
                            "ANALYSIS_FAILED",
                        )
                    )
                else:
                    execution.record_stock_success(stock.symbol)
                    outcomes.append(
                        AnalysisRunOutcome.success(
                            stock.symbol,
                            stock.id,
                        )
                    )

            self._analysis_run_store.save(
                analysis_run.with_outcomes(tuple(outcomes))
            )

        execution.finish()
        self._analysis_run_store.save(
            analysis_run
            .with_outcomes(tuple(outcomes))
            .with_state(execution.state)
        )
        return MarketAnalysisResult(
            execution=execution,
            analysis_run_id=analysis_run.id,
        )

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
