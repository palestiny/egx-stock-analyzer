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


def test_health_returns_ok():
    app = create_app(InMemoryAnalysisResultStore())

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
    assert response.json() == {"detail": "Analysis execution failed"}


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


def test_post_analysis_runs_application_capability_and_returns_stored_result():
    store = InMemoryAnalysisResultStore()

    class SuccessfulRunner:
        def execute(self, symbol, as_of):
            assert symbol == "EGAL"
            store.save(symbol, make_result())

    app = create_app(store, SuccessfulRunner())

    with TestClient(app) as client:
        response = client.post("/api/v1/analysis/EGAL")

    assert response.status_code == 200
    assert response.json() == {
        "symbol": "EGAL",
        "technical_score": 26,
        "fundamental_score": 21,
        "stock_quality": 47,
        "entry_quality": 13,
        "opportunity": "watch",
    }


def test_post_analysis_returns_500_when_execution_does_not_store_result():
    store = InMemoryAnalysisResultStore()

    class SuccessfulRunner:
        def execute(self, symbol, as_of):
            assert symbol == "EGAL"

    app = create_app(store, SuccessfulRunner())

    with TestClient(app) as client:
        response = client.post("/api/v1/analysis/EGAL")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Analysis result was not stored for EGAL",
    }


def test_post_market_analysis_returns_503_when_execution_is_not_configured():
    app = create_app(InMemoryAnalysisResultStore())

    with TestClient(app) as client:
        response = client.post("/api/v1/market-analysis")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Market analysis execution is not configured",
    }


def test_post_market_analysis_returns_aggregate_execution_result():
    class SuccessfulMarketRunner:
        def execute(self, as_of):
            from app.domain.execution import Execution

            execution = Execution.create()
            execution.start()
            execution.record_stock_success("EGAL")
            execution.record_stock_success("IEEC")
            execution.finish()
            return execution

    app = create_app(
        InMemoryAnalysisResultStore(),
        run_configured_market_analysis=SuccessfulMarketRunner(),
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/market-analysis")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "completed"
    assert body["successful_stock_ids"] == ["EGAL", "IEEC"]
    assert body["failed_stock_ids"] == []
    assert body["failure_reasons"] == {}
    assert body["execution_id"]


def test_post_market_analysis_hides_internal_execution_errors():
    class FailingMarketRunner:
        def execute(self, as_of):
            raise RuntimeError("provider internals must not leak")

    app = create_app(
        InMemoryAnalysisResultStore(),
        run_configured_market_analysis=FailingMarketRunner(),
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/market-analysis")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Market-wide analysis execution failed",
    }
