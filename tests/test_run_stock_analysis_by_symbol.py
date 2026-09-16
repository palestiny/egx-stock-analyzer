from datetime import date
from uuid import uuid4

import pytest

from app.application.analysis.run_stock_analysis_by_symbol import RunStockAnalysisBySymbol
from app.domain.stocks.stock import Stock


class FakeRunStockAnalysis:
    def __init__(self) -> None:
        self.calls: list[tuple[Stock, date]] = []

    def execute(self, stock: Stock, as_of: date) -> None:
        self.calls.append((stock, as_of))


class FakeStockCatalog:
    def __init__(self, stock: Stock | None) -> None:
        self.stock = stock
        self.calls: list[str] = []

    def get(self, symbol: str) -> Stock | None:
        self.calls.append(symbol)
        return self.stock if symbol.strip().upper() == self.stock.symbol else None if self.stock else None


def test_runs_analysis_for_cataloged_symbol() -> None:
    stock = Stock.create("EGAL", "Egypt Aluminum")
    catalog = FakeStockCatalog(stock)
    runner = FakeRunStockAnalysis()

    RunStockAnalysisBySymbol(catalog, runner).execute(
        " egal ",
        date(2026, 9, 16),
    )

    assert catalog.calls == [" egal "]
    assert runner.calls == [(stock, date(2026, 9, 16))]


def test_rejects_unknown_symbol() -> None:
    catalog = FakeStockCatalog(None)
    runner = FakeRunStockAnalysis()

    with pytest.raises(ValueError, match="Unknown stock symbol: UNKNOWN"):
        RunStockAnalysisBySymbol(catalog, runner).execute(
            "UNKNOWN",
            date(2026, 9, 16),
        )

    assert runner.calls == []
