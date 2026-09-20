from datetime import date
from unittest.mock import Mock

import pytest

from app.application.analysis.run_market_analysis import (
    DuplicateMarketAnalysisSymbolError,
    RunMarketAnalysis,
)
from app.application.stocks.catalog import InMemoryStockCatalog
from app.application.analysis.run_store import InMemoryAnalysisRunStore
from app.domain.execution import ExecutionState
from app.domain.stocks.stock import Stock


AS_OF = date(2026, 9, 18)


def make_runner(stocks: list[Stock]):
    catalog = InMemoryStockCatalog(stocks)
    run_stock_analysis = Mock()
    runner = RunMarketAnalysis(catalog, run_stock_analysis)
    return runner, run_stock_analysis


def test_empty_universe_completes_without_running_stock_analysis():
    runner, run_stock_analysis = make_runner([])

    result = runner.execute([], AS_OF)

    assert result.execution.state is ExecutionState.COMPLETED
    assert result.execution.successful_stock_ids == set()
    assert result.execution.failed_stock_ids == set()
    run_stock_analysis.execute.assert_not_called()


def test_one_stock_success_completes():
    stocks = [Stock.create("EGAL", "Egypt Aluminum")]
    runner, run_stock_analysis = make_runner(stocks)

    result = runner.execute(["egal"], AS_OF)

    assert result.execution.state is ExecutionState.COMPLETED
    assert result.execution.successful_stock_ids == {"EGAL"}
    assert result.execution.failed_stock_ids == set()
    run_stock_analysis.execute.assert_called_once()


def test_runs_multiple_stocks_in_supplied_order():
    stocks = [
        Stock.create("EGAL", "Egypt Aluminum"),
        Stock.create("IEEC", "Egyptian Electrical"),
    ]
    runner, run_stock_analysis = make_runner(stocks)
    calls = []
    run_stock_analysis.execute.side_effect = lambda stock, as_of, analysis_run_id: calls.append(stock.symbol)

    result = runner.execute(["IEEC", "EGAL"], AS_OF)

    assert result.execution.state is ExecutionState.COMPLETED
    assert calls == ["IEEC", "EGAL"]


def test_unknown_symbol_is_recorded_as_failure_and_later_stock_still_runs():
    stocks = [Stock.create("EGAL", "Egypt Aluminum")]
    runner, run_stock_analysis = make_runner(stocks)

    result = runner.execute(["UNKNOWN", "EGAL"], AS_OF)

    assert result.execution.state is ExecutionState.COMPLETED_WITH_ERRORS
    assert result.execution.failed_stock_ids == {"UNKNOWN"}
    assert result.execution.successful_stock_ids == {"EGAL"}
    assert result.execution.failure_reasons["UNKNOWN"] == "Unknown stock symbol: UNKNOWN"
    run_stock_analysis.execute.assert_called_once()


def test_stock_failure_does_not_erase_previous_success():
    stocks = [
        Stock.create("EGAL", "Egypt Aluminum"),
        Stock.create("IEEC", "Egyptian Electrical"),
    ]
    runner, run_stock_analysis = make_runner(stocks)

    def execute(stock, as_of, analysis_run_id):
        if stock.symbol == "IEEC":
            raise RuntimeError("provider unavailable")

    run_stock_analysis.execute.side_effect = execute

    result = runner.execute(["EGAL", "IEEC"], AS_OF)

    assert result.execution.state is ExecutionState.COMPLETED_WITH_ERRORS
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

    with pytest.raises(
        DuplicateMarketAnalysisSymbolError,
        match="Duplicate stock symbol: EGAL",
    ):
        runner.execute(["EGAL", " egal "], AS_OF)

    run_stock_analysis.execute.assert_not_called()


def test_each_market_run_has_its_own_execution_identity():
    stocks = [Stock.create("EGAL", "Egypt Aluminum")]
    runner, _ = make_runner(stocks)

    first = runner.execute(["EGAL"], AS_OF)
    second = runner.execute(["EGAL"], AS_OF)

    assert first.execution.id != second.execution.id


def test_market_orchestrator_does_not_duplicate_per_stock_retries():
    stocks = [Stock.create("EGAL", "Egypt Aluminum")]
    runner, run_stock_analysis = make_runner(stocks)
    run_stock_analysis.execute.side_effect = RuntimeError("transient")

    result = runner.execute(["EGAL"], AS_OF)

    assert result.execution.state is ExecutionState.FAILED
    assert run_stock_analysis.execute.call_count == 1


def test_empty_symbol_is_rejected_before_execution():
    stocks = [Stock.create("EGAL", "Egypt Aluminum")]
    runner, run_stock_analysis = make_runner(stocks)

    with pytest.raises(ValueError, match="Stock symbol cannot be empty"):
        runner.execute(["EGAL", "  "], AS_OF)

    run_stock_analysis.execute.assert_not_called()



def test_market_run_persists_same_analysis_run_identity_used_for_stock_execution():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    catalog = InMemoryStockCatalog([stock])
    run_stock_analysis = Mock()
    run_store = InMemoryAnalysisRunStore()
    runner = RunMarketAnalysis(catalog, run_stock_analysis, run_store)

    result = runner.execute(["EGAL"], AS_OF)

    persisted = run_store.get(result.analysis_run_id)

    assert persisted is not None
    assert persisted.state is ExecutionState.COMPLETED
    run_stock_analysis.execute.assert_called_once_with(
        stock,
        AS_OF,
        analysis_run_id=result.analysis_run_id,
    )


def test_market_run_persists_safe_outcomes_without_raw_failure_text():
    stocks = [
        Stock.create("EGAL", "Egypt Aluminum"),
        Stock.create("IEEC", "Egyptian Electrical"),
    ]
    runner, run_stock_analysis = make_runner(stocks)

    def execute(stock, as_of, analysis_run_id):
        if stock.symbol == "IEEC":
            raise RuntimeError("provider secret=should-not-persist")

    run_stock_analysis.execute.side_effect = execute

    result = runner.execute(["EGAL", "IEEC"], AS_OF)
    persisted = runner._analysis_run_store.get(result.analysis_run_id)

    assert persisted is not None
    assert persisted.outcomes_available is True
    assert [item.symbol for item in persisted.outcomes] == ["EGAL", "IEEC"]
    assert persisted.outcomes[0].state.value == "success"
    assert persisted.outcomes[1].failure_code == "ANALYSIS_FAILED"
    assert persisted.outcomes[1].failure_detail is None


def test_market_run_propagates_user_owner_to_correlated_stock_analysis():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    runner, run_stock_analysis = make_runner([stock])
    owner_id = __import__("uuid").uuid4()

    result = runner.execute(["EGAL"], AS_OF, owner_user_id=owner_id)

    assert result.execution.state is ExecutionState.COMPLETED
    run_stock_analysis.execute.assert_called_once_with(
        stock,
        AS_OF,
        analysis_run_id=result.analysis_run_id,
        owner_user_id=owner_id,
    )
