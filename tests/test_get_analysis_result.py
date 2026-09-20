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


def test_get_analysis_result_only_returns_owned_snapshot_for_user():
    from uuid import uuid4
    from app.application.security.identity import AuthenticatedIdentity

    result = Mock(spec=StockAnalysisResult)
    store = InMemoryAnalysisResultStore()
    owner_id = uuid4()
    other_owner_id = uuid4()
    store.save("EGAL", result, owner_user_id=owner_id)
    store.save("EGAL", Mock(spec=StockAnalysisResult), owner_user_id=other_owner_id)

    query = GetAnalysisResult(store)

    assert query.execute("EGAL", identity=AuthenticatedIdentity.user(owner_id)) is result
    assert query.execute("EGAL", identity=AuthenticatedIdentity.user(other_owner_id)) is not result
