from unittest.mock import Mock

from app.application.analysis.stock_analysis import StockAnalysisResult
from app.application.analysis.result_store import InMemoryAnalysisResultStore


def test_analysis_result_store_saves_and_gets_result_by_symbol():
    result = Mock(spec=StockAnalysisResult)
    store = InMemoryAnalysisResultStore()

    store.save("COMI", result)

    assert store.get("COMI") is result
