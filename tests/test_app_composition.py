from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.runtime import InfrastructureRuntime
from app.main import (
    create_application,
    create_application_from_environment,
    create_development_application_from_environment,
)


@dataclass
class FakeApplicationRuntime:
    result_store: InMemoryAnalysisResultStore
    run_by_symbol: object | None = None
    get_analysis_report: object | None = None
    get_alert_candidate: object | None = None
    get_market_opportunity_ranking: object | None = None


class FakeRuntime:
    def __init__(self, result_store: InMemoryAnalysisResultStore) -> None:
        self.application_runtime = FakeApplicationRuntime(
            result_store,
            run_by_symbol=object(),
            get_analysis_report=object(),
            get_alert_candidate=object(),
            get_market_opportunity_ranking=object(),
        )
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_create_application_uses_runtime_result_store() -> None:
    result_store = InMemoryAnalysisResultStore()
    runtime = FakeRuntime(result_store)

    app = create_application(runtime)

    assert app is not None
    with TestClient(app) as client:
        assert client.get("/api/v1/analysis/UNKNOWN").status_code == 404
    assert runtime.closed is True



def test_create_application_exposes_health_endpoint_and_closes_runtime() -> None:
    result_store = InMemoryAnalysisResultStore()
    runtime = FakeRuntime(result_store)

    app = create_application(runtime)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert runtime.closed is True

def test_existing_create_app_contract_remains_unchanged() -> None:
    result_store = InMemoryAnalysisResultStore()
    app = create_app(result_store)

    with TestClient(app) as client:
        assert client.get("/api/v1/analysis/UNKNOWN").status_code == 404


def test_create_application_from_environment_loads_config_at_composition_root(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}
    runtime = FakeRuntime(InMemoryAnalysisResultStore())

    def fake_create_infrastructure_runtime(**kwargs):
        captured.update(kwargs)
        return runtime

    monkeypatch.setattr("app.main.create_infrastructure_runtime", fake_create_infrastructure_runtime)

    stock_catalog = InMemoryStockCatalog([Stock.create("EGAL", "Egypt Aluminum")])
    app = create_application_from_environment(stock_catalog)

    assert app is not None
    assert captured["stock_catalog"] is stock_catalog
    assert isinstance(captured["config"], InfrastructureConfig)
    assert captured["config"] == InfrastructureConfig()
    assert captured["yfinance_module"].__name__ == "yfinance"

    with TestClient(app):
        pass

    assert runtime.closed is True


def test_create_development_application_from_environment_uses_development_catalog(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    captured: dict[str, object] = {}
    runtime = FakeRuntime(InMemoryAnalysisResultStore())

    def fake_create_infrastructure_runtime(**kwargs):
        captured.update(kwargs)
        return runtime

    monkeypatch.setattr(
        "app.main.create_infrastructure_runtime",
        fake_create_infrastructure_runtime,
    )

    app = create_development_application_from_environment()

    assert app is not None
    catalog = captured["stock_catalog"]
    assert catalog.get("EGAL") is not None
    assert catalog.get("EGAL").name == "Egypt Aluminum"

    with TestClient(app):
        pass

    assert runtime.closed is True

