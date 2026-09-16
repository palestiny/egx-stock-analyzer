from datetime import date

import pytest

from app.application.analysis.run_stock_analysis_by_symbol import RunStockAnalysisBySymbol
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock


class FakeRunStockAnalysis:
    def __init__(self) -> None:
        self.calls = []

    def execute(self, stock: Stock, as_of: date) -> None:
        self.calls.append((stock, as_of))


def test_runs_analysis_for_cataloged_symbol():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    catalog = InMemoryStockCatalog([stock])
    runner = FakeRunStockAnalysis()
    use_case = RunStockAnalysisBySymbol(catalog, runner)

    as_of = date(2026, 9, 16)
    use_case.execute(" egal ", as_of)

    assert runner.calls == [(stock, as_of)]


def test_rejects_unknown_symbol():
    catalog = InMemoryStockCatalog([])
    runner = FakeRunStockAnalysis()
    use_case = RunStockAnalysisBySymbol(catalog, runner)

    with pytest.raises(ValueError, match="Unknown stock symbol: UNKNOWN"):
        use_case.execute("UNKNOWN", date(2026, 9, 16))
