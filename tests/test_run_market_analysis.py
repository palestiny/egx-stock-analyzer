from datetime import date
from unittest.mock import Mock

import pytest

from app.application.analysis.run_market_analysis import (
    InvalidMarketUniverseError,
    RunMarketAnalysis,
)
from app.domain.execution import ExecutionState
from app.domain.stocks.stock import Stock


def make_stock(symbol: str) -> Stock:
    return Stock.create(symbol, f"{symbol} Company")


def make_runner():
    return Mock()


def test_empty_universe_is_completed_no_op():
    catalog = Mock()
    runner = make_runner()

    result = RunMarketAnalysis(catalog, runner).execute([], date(2026, 9, 18))

    assert result.state is ExecutionState.COMPLETED
    assert result.successful_stock_ids == set()
    assert result.failed_stock_ids == set()
    catalog.get.assert_not_called()
    runner.execute.assert_not_called()


def test_single_stock_success_is_completed():
    stock = make_stock("EGAL")
    catalog = Mock()
    catalog.get.return_value = stock
    runner = make_runner()

    result = RunMarketAnalysis(catalog, runner).execute(
        ["egal"], date(2026, 9, 18)
    )

    catalog.get.assert_called_once_with("EGAL")
    runner.execute.assert_called_once_with(stock, date(2026, 9, 18))
    assert result.state is ExecutionState.COMPLETED
    assert result.successful_stock_ids == {"EGAL"}


def test_multiple_stocks_execute_in_supplied_order():
    stocks = [make_stock("EGAL"), make_stock("IEEC"), make_stock("COMI")]
    catalog = Mock()
    catalog.get.side_effect = stocks
    runner = make_runner()

    result = RunMarketAnalysis(catalog, runner).execute(
        ["EGAL", "IEEC", "COMI"], date(2026, 9, 18)
    )

    assert result.state is ExecutionState.COMPLETED
    assert [call.args[0].symbol for call in runner.execute.call_args_list] == [
        "EGAL",
        "IEEC",
        "COMI",
    ]


def test_one_failure_does_not_stop_later_stocks():
    stocks = [make_stock("EGAL"), make_stock("IEEC"), make_stock("COMI")]
    catalog = Mock()
    catalog.get.side_effect = stocks
    runner = make_runner()
    runner.execute.side_effect = [None, RuntimeError("analysis failed"), None]

    result = RunMarketAnalysis(catalog, runner).execute(
        ["EGAL", "IEEC", "COMI"], date(2026, 9, 18)
    )

    assert result.state is ExecutionState.COMPLETED_WITH_ERRORS
    assert result.successful_stock_ids == {"EGAL", "COMI"}
    assert result.failed_stock_ids == {"IEEC"}
    assert result.failure_reasons == {"IEEC": "analysis failed"}


def test_all_stocks_failed_returns_failed():
    stocks = [make_stock("EGAL"), make_stock("IEEC")]
    catalog = Mock()
    catalog.get.side_effect = stocks
    runner = make_runner()
    runner.execute.side_effect = [
        RuntimeError("eg failure"),
        RuntimeError("ie failure"),
    ]

    result = RunMarketAnalysis(catalog, runner).execute(
        ["EGAL", "IEEC"], date(2026, 9, 18)
    )

    assert result.state is ExecutionState.FAILED
    assert result.failed_stock_ids == {"EGAL", "IEEC"}


def test_unknown_symbol_is_individual_failure_and_later_stocks_continue():
    stock = make_stock("EGAL")
    catalog = Mock()
    catalog.get.side_effect = [None, stock]
    runner = make_runner()

    result = RunMarketAnalysis(catalog, runner).execute(
        ["UNKNOWN", "EGAL"], date(2026, 9, 18)
    )

    assert result.state is ExecutionState.COMPLETED_WITH_ERRORS
    assert result.failed_stock_ids == {"UNKNOWN"}
    assert result.successful_stock_ids == {"EGAL"}
    assert result.failure_reasons["UNKNOWN"] == "Unknown stock symbol: UNKNOWN"
    runner.execute.assert_called_once_with(stock, date(2026, 9, 18))


def test_duplicate_normalized_symbols_are_rejected_before_execution():
    catalog = Mock()
    runner = make_runner()

    with pytest.raises(
        InvalidMarketUniverseError,
        match="Duplicate stock symbol",
    ):
        RunMarketAnalysis(catalog, runner).execute(
            ["EGAL", " egal "], date(2026, 9, 18)
        )

    catalog.get.assert_not_called()
    runner.execute.assert_not_called()


def test_empty_symbol_is_rejected_before_execution():
    catalog = Mock()
    runner = make_runner()

    with pytest.raises(
        InvalidMarketUniverseError,
        match="empty stock symbol",
    ):
        RunMarketAnalysis(catalog, runner).execute(
            ["EGAL", "  "], date(2026, 9, 18)
        )

    catalog.get.assert_not_called()
    runner.execute.assert_not_called()


def test_market_run_has_execution_identity():
    result = RunMarketAnalysis(Mock(), Mock()).execute([], date(2026, 9, 18))

    assert result.id is not None
