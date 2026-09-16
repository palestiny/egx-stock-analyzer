from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.infrastructure.runtime import InfrastructureRuntime
from app.main import create_application


@dataclass
class FakeApplicationRuntime:
    result_store: InMemoryAnalysisResultStore


def test_create_application_uses_runtime_result_store() -> None:
    result_store = InMemoryAnalysisResultStore()
    runtime = InfrastructureRuntime(
        application_runtime=FakeApplicationRuntime(result_store),
        market_data_provider=None,
        fundamental_data_provider=None,
        _finnhub_client=None,
    )

    app = create_application(runtime)

    assert app is not None
    assert TestClient(app).get("/api/v1/analysis/UNKNOWN").status_code == 404


def test_existing_create_app_contract_remains_unchanged() -> None:
    result_store = InMemoryAnalysisResultStore()
    app = create_app(result_store)

    assert TestClient(app).get("/api/v1/analysis/UNKNOWN").status_code == 404
