from datetime import date
from types import SimpleNamespace

from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.reporting.get_analysis_report import GetAnalysisReport
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock


def make_result():
    return SimpleNamespace(
        technical_analysis=SimpleNamespace(),
        fundamental_analysis=SimpleNamespace(),
        stock_quality=SimpleNamespace(total_score=47),
        entry_context=SimpleNamespace(),
        entry_quality=SimpleNamespace(total_score=13),
        opportunity=SimpleNamespace(),
    )


def test_get_analysis_report_returns_none_when_stock_is_unknown():
    use_case = GetAnalysisReport(
        InMemoryStockCatalog([]),
        InMemoryAnalysisResultStore(),
    )

    assert use_case.execute("UNKNOWN") is None


def test_get_analysis_report_returns_none_when_result_is_missing():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    use_case = GetAnalysisReport(
        InMemoryStockCatalog([stock]),
        InMemoryAnalysisResultStore(),
    )

    assert use_case.execute("EGAL") is None


def test_get_analysis_report_uses_stored_analysis_date():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store = InMemoryAnalysisResultStore()
    store.save("EGAL", make_result(), analysis_date=date(2026, 9, 16))
    use_case = GetAnalysisReport(InMemoryStockCatalog([stock]), store)

    report = use_case.execute("EGAL")

    assert report is not None
    assert report.stock_id == stock.id
    assert report.stock_symbol == "EGAL"
    assert report.analysis_date == date(2026, 9, 16)
    assert report.stock_quality.total_score == 47
    assert report.entry_quality.total_score == 13


def test_get_analysis_report_returns_none_for_legacy_result_without_analysis_date():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store = InMemoryAnalysisResultStore()
    store.save("EGAL", make_result())
    use_case = GetAnalysisReport(InMemoryStockCatalog([stock]), store)

    assert use_case.execute("EGAL") is None
