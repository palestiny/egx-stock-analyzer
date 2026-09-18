from unittest.mock import Mock

from app.application.analysis.run_configured_market_analysis import (
    RunConfiguredMarketAnalysis,
)
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.execution import Execution, ExecutionState
from app.domain.stocks.stock import Stock


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
    run_market_analysis.execute.return_value = _execution(ExecutionState.COMPLETED)

    capability = RunConfiguredMarketAnalysis(catalog, run_market_analysis)

    result = capability.execute()

    assert result.state is ExecutionState.COMPLETED
    run_market_analysis.execute.assert_called_once_with(["EGAL", "IEEC"], result.created_at if hasattr(result, "created_at") else result)
