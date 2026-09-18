from datetime import date

import pytest

from app.application.analysis.run_market_analysis import RunMarketAnalysis
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.execution import ExecutionState
from app.domain.stocks.stock import Stock


class FakeRunStockAnalysis:
    def __init__(self, failures: dict[str, Exception] | None = None) -> None:
        self.failures = failures or {}
        self.calls: list[str] = []

    def execute(self, stock: Stock, as_of: date) -> None:
        self.calls.append(stock.symbol)
        failure = self.failures.get(stock.symbol)
        if failure is not None:
            raise failure


def make_catalog(*symbols: str) -> InMemoryStockCatalog:
    return InMemoryStockCatalog(
        [Stock.create(symbol, f"{symbol} Company") for symbol in symbols]
    )


def test_empty_universe_completes_without_stock_execution():
    runner = FakeRunStockAnalysis()
    use_case = RunMarketAnalysis(make_catalog("EGAL"), runner)

    result = use_case.execute([], date(2026, 9, 18))

    assert result.state is ExecutionState.COMPLETED
    assert result.successful_stock_ids == set()
    assert result.failed_stock_ids == set()
    assert runner.calls == []


def test_one_stock_success_completes():
    runner = FakeRunStockAnalysis()
    use_case = RunMarketAnalysis(make_catalog("EGAL"), runner)

    result = use_case.execute(["EGAL"], date(2026, 9, 18))

    assert result.state is ExecutionState.COMPLETED
    assert result.successful_stock_ids == {"EGAL"}
    assert result.failed_stock_ids == set()


def test_multiple_stocks_execute_in_supplied_order():
    runner = FakeRunStockAnalysis()
    use_case = RunMarketAnalysis(make_catalog("EGAL", "COMI", "IEEC"), runner)

    result = use_case.execute(["ieec", "EGAL", "comi"], date(2026, 9, 18))

    assert result.state is ExecutionState.COMPLETED
    assert runner.calls == ["IEEC", "EGAL", "COMI"]


def test_one_failure_does_not_stop_later_stocks():
    runner = FakeRunStockAnalysis(
        failures={"EGAL": RuntimeError("market data unavailable")}
    )
    use_case = RunMarketAnalysis(make_catalog("COMI", "EGAL", "IEEC"), runner)

    result = use_case.execute(["COMI", "EGAL", "IEEC"], date(2026, 9, 18))

    assert result.state is ExecutionState.COMPLETED_WITH_ERRORS
    assert result.successful_stock_ids == {"COMI", "IEEC"}
    assert result.failed_stock_ids == {"EGAL"}
    assert result.failure_reasons["EGAL"] == "market data unavailable"
    assert runner.calls == ["COMI", "EGAL", "IEEC"]


def test_all_stocks_failing_returns_failed():
    runner = FakeRunStockAnalysis(
        failures={
            "EGAL": RuntimeError("EGAL failed"),
            "IEEC": RuntimeError("IEEC failed"),
        }
    )
    use_case = RunMarketAnalysis(make_catalog("EGAL", "IEEC"), runner)

    result = use_case.execute(["EGAL", "IEEC"], date(2026, 9, 18))

    assert result.state is ExecutionState.FAILED
    assert result.successful_stock_ids == set()
    assert result.failed_stock_ids == {"EGAL", "IEEC"}


def test_unknown_symbol_is_recorded_as_failure_and_later_stocks_continue():
    runner = FakeRunStockAnalysis()
    use_case = RunMarketAnalysis(make_catalog("IEEC"), runner)

    result = use_case.execute(["UNKNOWN", "IEEC"], date(2026, 9, 18))

    assert result.state is ExecutionState.COMPLETED_WITH_ERRORS
    assert result.failed_stock_ids == {"UNKNOWN"}
    assert "Unknown stock symbol: UNKNOWN" == result.failure_reasons["UNKNOWN"]
    assert result.successful_stock_ids == {"IEEC"}
    assert runner.calls == ["IEEC"]


def test_duplicate_normalized_symbols_are_rejected_before_execution():
    runner = FakeRunStockAnalysis()
    use_case = RunMarketAnalysis(make_catalog("EGAL"), runner)

    with pytest.raises(ValueError, match="Duplicate stock symbol"):
        use_case.execute(["EGAL", " egal "], date(2026, 9, 18))

    assert runner.calls == []


def test_successful_stocks_are_not_lost_when_a_later_stock_fails():
    runner = FakeRunStockAnalysis(
        failures={"IEEC": RuntimeError("IEEC failed")}
    )
    use_case = RunMarketAnalysis(make_catalog("EGAL", "IEEC"), runner)

    result = use_case.execute(["EGAL", "IEEC"], date(2026, 9, 18))

    assert result.successful_stock_ids == {"EGAL"}
    assert result.failed_stock_ids == {"IEEC"}


def test_each_market_run_has_its_own_execution_identity():
    runner = FakeRunStockAnalysis()
    use_case = RunMarketAnalysis(make_catalog("EGAL"), runner)

    first = use_case.execute(["EGAL"], date(2026, 9, 18))
    second = use_case.execute(["EGAL"], date(2026, 9, 18))

    assert first.id != second.id
