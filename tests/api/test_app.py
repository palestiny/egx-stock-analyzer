from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore


def test_app_returns_404_when_analysis_result_is_missing() -> None:
    app = create_app(InMemoryAnalysisResultStore())
    client = TestClient(app)

    response = client.get("/api/v1/analysis/EGAL")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Analysis result not found for EGAL",
    }
