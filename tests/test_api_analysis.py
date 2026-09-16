from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.stock_analysis import StockAnalysisResult


def test_get_analysis_returns_result_for_symbol():
    result = Mock(spec=StockAnalysisResult)
    store = Mock()
    store.get.return_value = result

    app = create_app(store)
    client = TestClient(app)

    response = client.get("/api/v1/analysis/EGAL")

    assert response.status_code == 200
    store.get.assert_called_once_with("EGAL")
