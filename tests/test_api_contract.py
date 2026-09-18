from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore


def make_result():
    return SimpleNamespace(
        technical_score=SimpleNamespace(total_score=26),
        fundamental_score=SimpleNamespace(total=21),
        stock_quality=SimpleNamespace(total_score=47),
        entry_quality=SimpleNamespace(total_score=13),
        opportunity=SimpleNamespace(classification=SimpleNamespace(value="watch")),
    )


def test_get_analysis_returns_404_when_result_does_not_exist():
    app = create_app(InMemoryAnalysisResultStore())

    with TestClient(app) as client:
        response = client.get("/api/v1/analysis/EGAL")

    assert response.status_code == 404
    assert response.json() == {"detail": "Analysis result not found for EGAL"}


def test_post_analysis_returns_503_when_execution_is_not_configured():
    app = create_app(InMemoryAnalysisResultStore())

    with TestClient(app) as client:
        response = client.post("/api/v1/analysis/EGAL")

    assert response.status_code == 503
    assert response.json() == {"detail": "Analysis execution is not configured"}


def test_post_analysis_returns_404_for_unknown_stock_symbol():
    class UnknownStockRunner:
        def execute(self, symbol, as_of):
            from app.application.analysis.run_stock_analysis_by_symbol import (
                UnknownStockSymbolError,
            )

            raise UnknownStockSymbolError(f"Unknown stock symbol: {symbol}")

    app = create_app(InMemoryAnalysisResultStore(), UnknownStockRunner())

    with TestClient(app) as client:
        response = client.post("/api/v1/analysis/UNKNOWN")

    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown stock symbol: UNKNOWN"}


def test_post_analysis_returns_500_when_analysis_execution_fails():
    class FailingRunner:
        def execute(self, symbol, as_of):
            raise RuntimeError("analysis failed")

    app = create_app(InMemoryAnalysisResultStore(), FailingRunner())

    with TestClient(app) as client:
        response = client.post("/api/v1/analysis/EGAL")

    assert response.status_code == 500
    assert response.json() == {"detail": "analysis failed"}


def test_get_analysis_returns_transport_dto():
    store = InMemoryAnalysisResultStore()
    store.save("EGAL", make_result())
    app = create_app(store)

    with TestClient(app) as client:
        response = client.get("/api/v1/analysis/EGAL")

    assert response.status_code == 200
    assert response.json() == {
        "symbol": "EGAL",
        "technical_score": 26,
        "fundamental_score": 21,
        "stock_quality": 47,
        "entry_quality": 13,
        "opportunity": "watch",
    }
