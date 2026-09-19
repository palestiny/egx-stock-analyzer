from datetime import date

import pytest

from app.application.analysis.run_stock_analysis_by_symbol import (
    UnknownStockSymbolError,
)
from app.application.analysis.run_market_analysis import RunMarketAnalysis
from app.domain.execution import ExecutionState


class FakeRunStockAnalysisBySymbol:
    def __init__(self, failures=None):
        self.calls = []
        self.failures = failures or {}

    def execute(self, symbol: str, as_of: date) -> None:
        self.calls.append((symbol, as_of))
        error = self.failures.get(symbol)
        if error is not None:
            raise error


def test_empty_universe_is_completed_no_op():
    runner = FakeRunStockAnalysisBySymbol()
    result = RunMarketAnalysis(runner).execute([], date(2026, 9, 18))

    assert result.execution.state is ExecutionState.COMPLETED
    assert result.execution.successful_stock_ids == set()
    assert result.execution.failed_stock_ids == set()
    assert runner.calls == []


def test_single_stock_success_is_completed():
    runner = FakeRunStockAnalysisBySymbol()
    result = RunMarketAnalysis(runner).execute(["egal"], date(2026, 9, 18))

    assert result.execution.state is ExecutionState.COMPLETED
    assert result.execution.successful_stock_ids == {"EGAL"}
    assert result.execution.failed_stock_ids == set()


def test_multiple_stocks_execute_in_supplied_order():
    runner = FakeRunStockAnalysisBySymbol()
    result = RunMarketAnalysis(runner).execute(
        ["EGAL", "IEEC", "COMI"],
        date(2026, 9, 18),
    )

    assert result.execution.state is ExecutionState.COMPLETED
    assert [symbol for symbol, _ in runner.calls] == ["EGAL", "IEEC", "COMI"]


def test_one_failure_does_not_stop_later_stocks():
    runner = FakeRunStockAnalysisBySymbol(
        failures={"IEEC": RuntimeError("analysis failed")}
    )

    result = RunMarketAnalysis(runner).execute(
        ["EGAL", "IEEC", "COMI"],
        date(2026, 9, 18),
    )

    assert result.execution.state is ExecutionState.COMPLETED_WITH_ERRORS
    assert result.execution.successful_stock_ids == {"EGAL", "COMI"}
    assert result.execution.failed_stock_ids == {"IEEC"}
    assert result.execution.failure_reasons["IEEC"] == "analysis failed"
    assert [symbol for symbol, _ in runner.calls] == ["EGAL", "IEEC", "COMI"]


def test_all_stocks_failed_returns_failed():
    runner = FakeRunStockAnalysisBySymbol(
        failures={
            "EGAL": RuntimeError("eg failure"),
            "IEEC": RuntimeError("ie failure"),
        }
    )

    result = RunMarketAnalysis(runner).execute(
        ["EGAL", "IEEC"],
        date(2026, 9, 18),
    )

    assert result.execution.state is ExecutionState.FAILED
    assert result.execution.failed_stock_ids == {"EGAL", "IEEC"}


def test_unknown_symbol_is_individual_failure():
    runner = FakeRunStockAnalysisBySymbol(
        failures={"UNKNOWN": UnknownStockSymbolError("Unknown stock symbol: UNKNOWN")}
    )

    result = RunMarketAnalysis(runner).execute(
        ["UNKNOWN", "EGAL"],
        date(2026, 9, 18),
    )

    assert result.execution.state is ExecutionState.COMPLETED_WITH_ERRORS
    assert result.execution.failed_stock_ids == {"UNKNOWN"}
    assert result.execution.successful_stock_ids == {"EGAL"}


def test_duplicate_normalized_symbols_are_rejected_before_execution():
    runner = FakeRunStockAnalysisBySymbol()

    with pytest.raises(ValueError, match="duplicate symbols"):
        RunMarketAnalysis(runner).execute(
            ["EGAL", " egal "],
            date(2026, 9, 18),
        )

    assert runner.calls == []
