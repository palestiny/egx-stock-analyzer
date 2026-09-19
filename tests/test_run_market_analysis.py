from datetime import date
from unittest.mock import Mock

import pytest

from app.application.analysis.run_market_analysis import RunMarketAnalysis
from app.domain.execution import ExecutionState
from app.domain.stocks.stock import Stock


def make_service(stock_symbols: list[str]) -> tuple[RunMarketAnalysis, Mock]:
    catalog = Mock()
    stocks = {symbol: Stock.create(symbol, f"{symbol} Company") for symbol in stock_symbols}
    catalog.get.side_effect = lambda symbol: stocks.get(symbol)
    run_stock_analysis = Mock()
    return RunMarketAnalysis(catalog, run_stock_analysis), run_stock_analysis


def test_empty_universe_completes_without_running_analysis():
    service, runner = make_service([])
    result = service.execute([], date(2026, 9, 18))
    assert result.execution.state is ExecutionState.COMPLETED
    assert result.execution.successful_stock_ids == set()
    assert result.execution.failed_stock_ids == set()
    runner.execute.assert_not_called()


def test_single_stock_success_completes():
    service, runner = make_service(["EGAL"])
    result = service.execute(["EGAL"], date(2026, 9, 18))
    assert result.execution.state is ExecutionState.COMPLETED
    assert result.execution.successful_stock_ids == {"EGAL"}
    assert result.execution.failed_stock_ids == set()
    runner.execute.assert_called_once()


def test_multiple_stocks_execute_in_supplied_order():
    service, runner = make_service(["EGAL", "IEEC", "EGAL2"])
    calls = []
    runner.execute.side_effect = lambda stock, as_of: calls.append(stock.symbol)
    result = service.execute(["IEEC", "EGAL", "EGAL2"], date(2026, 9, 18))
    assert result.execution.state is ExecutionState.COMPLETED
    assert calls == ["IEEC", "EGAL", "EGAL2"]


def test_one_failure_does_not_abort_later_stocks():
    service, runner = make_service(["EGAL", "IEEC", "EGAL2"])
    runner.execute.side_effect = [None, RuntimeError("analysis failed"), None]
    result = service.execute(["EGAL", "IEEC", "EGAL2"], date(2026, 9, 18))
    assert result.execution.state is ExecutionState.COMPLETED_WITH_ERRORS
    assert result.execution.successful_stock_ids == {"EGAL", "EGAL2"}
    assert result.execution.failed_stock_ids == {"IEEC"}
    assert result.execution.failure_reasons == {"IEEC": "analysis failed"}


def test_all_failures_return_failed():
    service, runner = make_service(["EGAL", "IEEC"])
    runner.execute.side_effect = RuntimeError("analysis failed")
    result = service.execute(["EGAL", "IEEC"], date(2026, 9, 18))
    assert result.execution.state is ExecutionState.FAILED
    assert result.execution.successful_stock_ids == set()
    assert result.execution.failed_stock_ids == {"EGAL", "IEEC"}


def test_unknown_symbol_is_an_individual_failure():
    service, runner = make_service(["EGAL"])
    result = service.execute(["EGAL", "UNKNOWN"], date(2026, 9, 18))
    assert result.execution.state is ExecutionState.COMPLETED_WITH_ERRORS
    assert result.execution.successful_stock_ids == {"EGAL"}
    assert result.execution.failed_stock_ids == {"UNKNOWN"}
    assert "Unknown stock symbol" in result.execution.failure_reasons["UNKNOWN"]
    assert runner.execute.call_count == 1


def test_duplicate_normalized_symbols_are_rejected_before_execution():
    service, runner = make_service(["EGAL"])
    with pytest.raises(ValueError, match="Duplicate stock symbol"):
        service.execute(["EGAL", " egal "], date(2026, 9, 18))
    runner.execute.assert_not_called()


def test_execution_has_an_identity():
    service, _ = make_service(["EGAL"])
    result = service.execute(["EGAL"], date(2026, 9, 18))
    assert result.execution.id is not None
