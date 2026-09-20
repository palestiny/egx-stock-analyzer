from datetime import date

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.get_analysis_run import GetAnalysisRun
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.analysis.run_store import InMemoryAnalysisRunStore
from app.domain.analysis_run import AnalysisRun
from app.domain.execution import ExecutionState


def make_app():
    run_store = InMemoryAnalysisRunStore()
    result_store = InMemoryAnalysisResultStore()
    run = AnalysisRun.create().with_state(ExecutionState.COMPLETED)
    run_store.save(run)
    result_store.save(
        "SVCE",
        object(),
        analysis_date=date(2026, 9, 20),
        analysis_run_id=run.id,
    )
    result_store.save(
        "EGAL",
        object(),
        analysis_date=date(2026, 9, 20),
        analysis_run_id=run.id,
    )
    capability = GetAnalysisRun(run_store, result_store)
    app = create_app(
        result_store,
        get_analysis_run=capability,
    )
    return app, run


def test_get_analysis_run_returns_read_model():
    app, run = make_app()

    with TestClient(app) as client:
        response = client.get(f"/api/v1/analysis-runs/{run.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == str(run.id)
    assert body["state"] == "completed"
    assert [item["symbol"] for item in body["snapshots"]] == ["EGAL", "SVCE"]
    assert body["next_cursor"] is None


def test_get_analysis_run_supports_bounded_pagination():
    app, run = make_app()

    with TestClient(app) as client:
        first = client.get(
            f"/api/v1/analysis-runs/{run.id}",
            params={"page_size": 1},
        )
        assert first.status_code == 200
        cursor = first.json()["next_cursor"]
        assert cursor is not None

        second = client.get(
            f"/api/v1/analysis-runs/{run.id}",
            params={"page_size": 1, "cursor": cursor},
        )

    assert second.status_code == 200
    assert [item["symbol"] for item in second.json()["snapshots"]] == ["SVCE"]
    assert second.json()["next_cursor"] is None


def test_get_analysis_run_returns_404_for_missing_run():
    app, _ = make_app()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/analysis-runs/00000000-0000-0000-0000-000000000001"
        )

    assert response.status_code == 404


def test_get_analysis_run_returns_400_for_invalid_page_size():
    app, run = make_app()

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/analysis-runs/{run.id}",
            params={"page_size": 101},
        )

    assert response.status_code == 400


def test_get_analysis_run_returns_503_when_not_configured():
    app = create_app(InMemoryAnalysisResultStore())

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/analysis-runs/00000000-0000-0000-0000-000000000001"
        )

    assert response.status_code == 503
