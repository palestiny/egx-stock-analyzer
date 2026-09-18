from datetime import date
from unittest.mock import Mock

import pytest

from app.application.analysis.run_market_analysis import (
    DuplicateMarketAnalysisSymbolError,
    RunMarketAnalysis,
)
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.execution import ExecutionState
from app.domain.stocks.stock import Stock


AS_OF = date(2026, 9, 18)


def make_runner(stocks: list[Stock]):
    catalog = InMemoryStockCatalog(stocks)
    run_stock_analysis = Mock()
    return RunMarketAnalysis(catalog, run_stock_analysis), run_stock_analysis


def test_empty_universe_completes_without_running_stock_analysis():
    runner, run_stock_analysis = make_runner([])

    result = runner.execute([], AS_OF)

    assert result.execution.state is ExecutionState.COMPLETED
    assert result.execution.successful_stock_ids == set()
    assert result.execution.failed_stock_ids == set()
    run_stock_analysis.execute.assert_not_called()


def test_runs_multiple_stocks_in_supplied_order():
    stocks = [
        Stock.create("EGAL", "Egypt Aluminum"),
        Stock.create("IEEC", "Egyptian Electrical"),
    ]
    runner, run_stock_analysis = make_runner(stocks)
    calls = []
    run_stock_analysis.execute.side_effect = lambda stock, as_of: calls.append(stock.symbol)

    result = runner.execute(["IEEC", "EGAL"], AS_OF)

    assert result.execution.state.value == "completed"
    assert calls == ["IEEC", "EGAL"]


def test_unknown_symbol_is_recorded_as_failure_and_later_stock_still_runs():
    stocks = [Stock.create("EGAL", "Egypt Aluminum")]
    runner, run_stock_analysis = make_runner(stocks)

    result = runner.execute(["UNKNOWN", "EGAL"], AS_OF)

    assert result.execution.state is ExecutionState.COMPLETED_WITH_ERRORS
    assert result.execution.failed_stock_ids == {"UNKNOWN"}
    assert result.execution.successful_stock_ids == {"EGAL"}
    assert "Unknown stock symbol: UNKNOWN" in result.execution.failure_reasons["UNKNOWN"]
    run_stock_analysis.execute.assert_called_once()


def test_stock_failure_does_not_erase_previous_success():
    stocks = [
        Stock.create("EGAL", "Egypt Aluminum"),
        Stock.create("IEEC", "Egyptian Electrical"),
    ]
    runner, run_stock_analysis = make_runner(stocks)

    def execute(stock, as_of):
        if stock.symbol == "IEEC":
            raise RuntimeError("provider unavailable")

    run_stock_analysis.execute.side_effect = execute

    result = runner.execute(["EGAL", "IEEC"], AS_OF)

    assert result.execution.state.value == "completed_with_errors"
    assert result.execution.successful_stock_ids == {"EGAL"}
    assert result.execution.failed_stock_ids == {"IEEC"}
    assert result.execution.failure_reasons == {"IEEC": "provider unavailable"}


def test_all_stock_failures_return_failed():
    stocks = [
        Stock.create("EGAL", "Egypt Aluminum"),
        Stock.create("IEEC", "Egyptian Electrical"),
    ]
    runner, run_stock_analysis = make_runner(stocks)
    run_stock_analysis.execute.side_effect = RuntimeError("analysis failed")

    result = runner.execute(["EGAL", "IEEC"], AS_OF)

    assert result.execution.state is ExecutionState.FAILED
    assert result.execution.successful_stock_ids == set()
    assert result.execution.failed_stock_ids == {"EGAL", "IEEC"}


def test_duplicate_normalized_symbols_are_rejected_before_execution():
    stocks = [Stock.create("EGAL", "Egypt Aluminum")]
    runner, run_stock_analysis = make_runner(stocks)

    with pytest.raises(DuplicateMarketAnalysisSymbolError, match="Duplicate stock symbol"):
        runner.execute(["EGAL", " egal "], AS_OF)

    run_stock_analysis.execute.assert_not_called()
