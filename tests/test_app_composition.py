from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.infrastructure.runtime import InfrastructureRuntime
from app.main import create_application


@dataclass
class FakeApplicationRuntime:
    result_store: InMemoryAnalysisResultStore


class FakeRuntime:
    def __init__(self, result_store: InMemoryAnalysisResultStore) -> None:
        self.application_runtime = FakeApplicationRuntime(result_store)
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


def test_existing_create_app_contract_remains_unchanged() -> None:
    result_store = InMemoryAnalysisResultStore()
    app = create_app(result_store)

    with TestClient(app) as client:
        assert client.get("/api/v1/analysis/UNKNOWN").status_code == 404
