from datetime import date
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.stock_analysis import StockAnalysisResult
from app.application.analysis.run_stock_analysis_by_symbol import RunStockAnalysisBySymbol, UnknownStockSymbolError
from app.domain.entry_analysis.scoring import EntryQualityScore
from app.domain.fundamental_analysis.scoring import FundamentalScore
from app.domain.opportunity.classification import OpportunityClassification, OpportunityClassificationResult
from app.domain.scoring.stock_quality import StockQualityScore
from app.domain.technical_analysis.scoring import TechnicalScore


def make_result() -> StockAnalysisResult:
    result = Mock(spec=StockAnalysisResult)
    result.technical_score = TechnicalScore(1, 0, -1, 0)
    result.fundamental_score = FundamentalScore(2, ())
    result.stock_quality = StockQualityScore(
        fundamental_score=result.fundamental_score,
        technical_score=result.technical_score,
        total_score=2,
    )
    result.entry_quality = EntryQualityScore(1, 0, 1)
    result.opportunity = OpportunityClassificationResult(OpportunityClassification.BUY)
    return result


def test_get_analysis_returns_response_dto_for_symbol():
    result = make_result()
    store = Mock()
    store.get.return_value = result

    app = create_app(store)
    client = TestClient(app)

    response = client.get("/api/v1/analysis/EGAL")

    assert response.status_code == 200
    assert response.json() == {
        "symbol": "EGAL",
        "technical_score": 0,
        "fundamental_score": 2,
        "stock_quality": 2,
        "entry_quality": 1,
        "opportunity": "buy",
    }
    store.get.assert_called_once_with("EGAL")


def test_get_analysis_returns_404_when_result_is_missing():
    store = Mock()
    store.get.return_value = None

    app = create_app(store)
    client = TestClient(app)

    response = client.get("/api/v1/analysis/EGAL")

    assert response.status_code == 404
    assert response.json() == {"detail": "Analysis result not found for EGAL"}


def test_post_analysis_runs_analysis_and_returns_result():
    result = make_result()
    store = Mock()
    store.get.return_value = result
    runner = Mock(spec=RunStockAnalysisBySymbol)

    app = create_app(store, runner)
    client = TestClient(app)

    response = client.post("/api/v1/analysis/EGAL")

    assert response.status_code == 200
    assert response.json()["symbol"] == "EGAL"
    runner.execute.assert_called_once_with("EGAL", date.today())
    store.get.assert_called_once_with("EGAL")


def test_post_analysis_returns_404_for_unknown_stock():
    store = Mock()
    runner = Mock(spec=RunStockAnalysisBySymbol)
    runner.execute.side_effect = UnknownStockSymbolError("Unknown stock symbol: UNKNOWN")

    app = create_app(store, runner)
    client = TestClient(app)

    response = client.post("/api/v1/analysis/UNKNOWN")

    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown stock symbol: UNKNOWN"}


def test_post_analysis_does_not_hide_analysis_input_value_errors():
    store = Mock()
    runner = Mock(spec=RunStockAnalysisBySymbol)
    runner.execute.side_effect = ValueError("Market data provider returned no observations")

    app = create_app(store, runner)
    client = TestClient(app)

    response = client.post("/api/v1/analysis/EGAL")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
