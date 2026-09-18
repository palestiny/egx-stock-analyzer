from datetime import date

import pytest

from app.application.analysis.run_market_analysis import (
    DuplicateStockSymbolError,
    RunMarketAnalysis,
)
from app.domain.execution import ExecutionState


class FakeRunStockAnalysisBySymbol:
    def __init__(self, failures=None):
        self.failures = failures or set()
        self.calls = []

    def execute(self, symbol: str, as_of: date) -> None:
        self.calls.append(symbol)
        if symbol in self.failures:
            raise RuntimeError(f"failed: {symbol}")


def test_empty_universe_is_completed_no_op():
    runner = FakeRunStockAnalysisBySymbol()
    result = RunMarketAnalysis(runner).execute([], date(2026, 9, 18))
    assert result.execution.state is ExecutionState.COMPLETED
    assert result.execution.successful_stock_ids == set()
    assert result.execution.failed_stock_ids == set()
    assert runner.calls == []


def test_multiple_stocks_execute_in_supplied_order():
    runner = FakeRunStockAnalysisBySymbol()
    result = RunMarketAnalysis(runner).execute([" EGAL ", "IEEC"], date(2026, 9, 18))
    assert result.execution.state is ExecutionState.COMPLETED
    assert runner.calls == ["EGAL", "IEEC"]
    assert result.execution.successful_stock_ids == {"EGAL", "IEEC"}


def test_one_failure_does_not_stop_later_stocks():
    runner = FakeRunStockAnalysisBySymbol(failures={"IEEC"})
    result = RunMarketAnalysis(runner).execute(["EGAL", "IEEC", "EFIC"], date(2026, 9, 18))
    assert result.execution.state is ExecutionState.COMPLETED_WITH_ERRORS
    assert result.execution.successful_stock_ids == {"EGAL", "EFIC"}
    assert result.execution.failed_stock_ids == {"IEEC"}
    assert "IEEC" in result.execution.failure_reasons
    assert runner.calls == ["EGAL", "IEEC", "EFIC"]


def test_all_failures_produce_failed_execution():
    runner = FakeRunStockAnalysisBySymbol(failures={"EGAL", "IEEC"})
    result = RunMarketAnalysis(runner).execute(["EGAL", "IEEC"], date(2026, 9, 18))
    assert result.execution.state is ExecutionState.FAILED
    assert result.execution.successful_stock_ids == set()
    assert result.execution.failed_stock_ids == {"EGAL", "IEEC"}


def test_duplicate_normalized_symbols_are_rejected_before_execution():
    runner = FakeRunStockAnalysisBySymbol()
    with pytest.raises(DuplicateStockSymbolError):
        RunMarketAnalysis(runner).execute(["EGAL", " egal "], date(2026, 9, 18))
    assert runner.calls == []


def test_unknown_symbol_is_an_individual_failure_and_later_stocks_continue():
    class UnknownSymbolRunner(FakeRunStockAnalysisBySymbol):
        def execute(self, symbol: str, as_of: date) -> None:
            self.calls.append(symbol)
            if symbol == "UNKNOWN":
                raise ValueError("Unknown stock symbol: UNKNOWN")

    runner = UnknownSymbolRunner()
    result = RunMarketAnalysis(runner).execute(["UNKNOWN", "EGAL"], date(2026, 9, 18))
    assert result.execution.state is ExecutionState.COMPLETED_WITH_ERRORS
    assert result.execution.failed_stock_ids == {"UNKNOWN"}
    assert result.execution.successful_stock_ids == {"EGAL"}
    assert runner.calls == ["UNKNOWN", "EGAL"]


def test_execution_has_aggregate_identity():
    runner = FakeRunStockAnalysisBySymbol()
    result = RunMarketAnalysis(runner).execute(["EGAL"], date(2026, 9, 18))
    assert result.execution.id is not None
