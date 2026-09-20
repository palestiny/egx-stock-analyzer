from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.list_analysis_runs import ListAnalysisRuns
from app.application.analysis.run_store import InMemoryAnalysisRunStore
from app.domain.analysis_run import AnalysisRun
from app.domain.execution import ExecutionState


def test_analysis_run_list_api_returns_empty_collection():
    run_store = InMemoryAnalysisRunStore()
    app = create_app(
        result_store=None,
        list_analysis_runs=ListAnalysisRuns(run_store),
    )

    response = TestClient(app).get("/api/v1/analysis-runs")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "has_more": False,
        "next_cursor": None,
    }


def test_analysis_run_list_api_supports_state_filter():
    run_store = InMemoryAnalysisRunStore()
    run_store.save(
        AnalysisRun(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            created_at=datetime(2026, 9, 20, 8, tzinfo=timezone.utc),
            state=ExecutionState.COMPLETED,
        )
    )
    run_store.save(
        AnalysisRun(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            created_at=datetime(2026, 9, 20, 9, tzinfo=timezone.utc),
            state=ExecutionState.FAILED,
        )
    )

    app = create_app(
        result_store=None,
        list_analysis_runs=ListAnalysisRuns(run_store),
    )

    response = TestClient(app).get(
        "/api/v1/analysis-runs",
        params={"state": "failed"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["run_id"] for item in body["items"]] == [
        "00000000-0000-0000-0000-000000000002"
    ]
    assert body["has_more"] is False


def test_analysis_run_list_api_rejects_invalid_state_and_cursor():
    run_store = InMemoryAnalysisRunStore()
    app = create_app(
        result_store=None,
        list_analysis_runs=ListAnalysisRuns(run_store),
    )

    invalid_state = TestClient(app).get(
        "/api/v1/analysis-runs",
        params={"state": "not-a-state"},
    )
    invalid_cursor = TestClient(app).get(
        "/api/v1/analysis-runs",
        params={"cursor": "invalid"},
    )

    assert invalid_state.status_code == 400
    assert invalid_cursor.status_code == 400
