from unittest.mock import Mock

from app.application.analysis.get_analysis_result import GetAnalysisResult
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.analysis.stock_analysis import StockAnalysisResult


def test_get_analysis_result_returns_saved_result():
    result = Mock(spec=StockAnalysisResult)
    store = InMemoryAnalysisResultStore()
    store.save("EGAL", result)

    query = GetAnalysisResult(store)

    assert query.execute("EGAL") is result


def test_get_analysis_result_returns_none_when_symbol_is_missing():
    query = GetAnalysisResult(InMemoryAnalysisResultStore())

    assert query.execute("EGAL") is None
