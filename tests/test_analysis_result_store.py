from datetime import date
from unittest.mock import Mock

import pytest

from app.application.analysis.stock_analysis import StockAnalysisResult
from app.application.analysis.result_store import InMemoryAnalysisResultStore


def test_analysis_result_store_saves_and_gets_result_by_symbol():
    result = Mock(spec=StockAnalysisResult)
    store = InMemoryAnalysisResultStore()

    store.save("COMI", result)

    assert store.get("COMI") is result


def test_in_memory_store_preserves_history_and_latest_result():
    first = Mock(spec=StockAnalysisResult)
    second = Mock(spec=StockAnalysisResult)
    store = InMemoryAnalysisResultStore()

    store.save("COMI", first)
    store.save("COMI", second)

    history = store.get_history("COMI")

    assert len(history) == 2
    assert history[0].result is second
    assert history[1].result is first
    assert store.get("COMI") is second


def test_in_memory_store_rejects_invalid_history_date_range():
    store = InMemoryAnalysisResultStore()

    with pytest.raises(ValueError, match="start_date cannot be after end_date"):
        store.get_history(
            "COMI",
            start_date=date(2026, 9, 18),
            end_date=date(2026, 9, 17),
        )
