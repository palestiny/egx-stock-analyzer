from fastapi.testclient import TestClient

from app.main import app


def test_app_returns_404_when_analysis_result_is_missing() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/analysis/EGAL")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Analysis result not found for EGAL",
    }
