from datetime import date
from unittest.mock import Mock

from app.application.analysis.run_configured_market_analysis import (
    MarketAnalysisResult,
    RunConfiguredMarketAnalysis,
)
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.execution import Execution, ExecutionState
from app.domain.stocks.stock import Stock


AS_OF = date(2026, 9, 18)


def _execution(state: ExecutionState) -> Execution:
    execution = Execution.create()
    execution.start()
    if state is ExecutionState.COMPLETED:
        execution.complete()
    elif state is ExecutionState.COMPLETED_WITH_ERRORS:
        execution.complete_with_errors()
    else:
        execution.fail()
    return execution


def test_configured_market_analysis_captures_catalog_snapshot_and_delegates():
    stocks = [
        Stock.create("EGAL", "Egypt Aluminum"),
        Stock.create("IEEC", "Egyptian Electrical"),
    ]
    catalog = InMemoryStockCatalog(stocks)
    run_market_analysis = Mock()
    expected = _execution(ExecutionState.COMPLETED)
    run_market_analysis.execute.return_value = MarketAnalysisResult(
        execution=expected,
        analysis_run_id=expected.id,
    )

    capability = RunConfiguredMarketAnalysis(catalog, run_market_analysis)

    result = capability.execute(AS_OF)

    assert result.execution is expected
    run_market_analysis.execute.assert_called_once_with(["EGAL", "IEEC"], AS_OF)


def test_empty_configured_universe_delegates_empty_snapshot():
    catalog = InMemoryStockCatalog([])
    run_market_analysis = Mock()
    expected = _execution(ExecutionState.COMPLETED)
    run_market_analysis.execute.return_value = MarketAnalysisResult(
        execution=expected,
        analysis_run_id=expected.id,
    )

    result = RunConfiguredMarketAnalysis(catalog, run_market_analysis).execute(AS_OF)

    assert result.execution is expected
    run_market_analysis.execute.assert_called_once_with([], AS_OF)


def test_catalog_snapshot_is_captured_once():
    class SnapshotCatalog:
        def __init__(self):
            self.calls = 0

        def symbols(self):
            self.calls += 1
            return ("EGAL", "IEEC")

    catalog = SnapshotCatalog()
    run_market_analysis = Mock()
    expected = _execution(ExecutionState.COMPLETED)
    run_market_analysis.execute.return_value = MarketAnalysisResult(
        execution=expected,
        analysis_run_id=expected.id,
    )

    RunConfiguredMarketAnalysis(catalog, run_market_analysis).execute(AS_OF)

    assert catalog.calls == 1
