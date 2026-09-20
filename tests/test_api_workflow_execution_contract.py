from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.execution.get_scheduled_workflow_executions import (
    ScheduledWorkflowExecutionReadModel,
)
from app.application.execution.scheduled_workflow_execution import ScheduledWorkflowExecutionState


def make_item(
    occurrence_id: str,
    state: ScheduledWorkflowExecutionState = ScheduledWorkflowExecutionState.COMPLETED,
) -> ScheduledWorkflowExecutionReadModel:
    workflow_state = state
    now = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
    return ScheduledWorkflowExecutionReadModel(
        id=uuid4(),
        occurrence_id=occurrence_id,
        state=workflow_state,
        created_at=now,
        updated_at=now,
        analysis_state="completed",
        delivery_state="completed",
    )


class FakeWorkflowExecutionQuery:
    def __init__(self, items=()):
        self.items = tuple(items)
        self.calls = []

    def execute(self, occurrence_id=None):
        self.calls.append(occurrence_id)
        if occurrence_id is None:
            return self.items
        return tuple(item for item in self.items if item.occurrence_id == occurrence_id)


def test_workflow_execution_history_returns_enveloped_items():
    query = FakeWorkflowExecutionQuery(
        [make_item("occ-1"), make_item("occ-2")]
    )
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_executions=query,
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/workflows/executions")

    assert response.status_code == 200
    payload = response.json()
    assert [item["occurrence_id"] for item in payload["items"]] == ["occ-1", "occ-2"]
    assert payload["items"][0]["state"] == "completed"
    assert query.calls == [None]


def test_workflow_execution_history_supports_exact_occurrence_filter():
    query = FakeWorkflowExecutionQuery(
        [make_item("occ-1"), make_item("occ-2")]
    )
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_executions=query,
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/workflows/executions",
            params={"occurrence_id": "occ-2"},
        )

    assert response.status_code == 200
    assert [item["occurrence_id"] for item in response.json()["items"]] == ["occ-2"]
    assert query.calls == ["occ-2"]


def test_workflow_execution_history_returns_404_for_missing_occurrence():
    query = FakeWorkflowExecutionQuery([make_item("occ-1")])
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_executions=query,
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/workflows/executions",
            params={"occurrence_id": "missing"},
        )

    assert response.status_code == 404


def test_workflow_execution_history_rejects_blank_occurrence_filter():
    query = FakeWorkflowExecutionQuery()
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_executions=query,
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/workflows/executions",
            params={"occurrence_id": "   "},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "occurrence_id cannot be empty"}
    assert query.calls == []


def test_workflow_execution_history_returns_503_when_not_configured():
    app = create_app(InMemoryAnalysisResultStore())

    with TestClient(app) as client:
        response = client.get("/api/v1/workflows/executions")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Scheduled workflow execution reporting is not configured"
    }


def test_workflow_execution_history_hides_store_failure_details():
    class FailingQuery:
        def execute(self, occurrence_id=None):
            raise RuntimeError("sqlite connection internals")

    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_executions=FailingQuery(),
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/workflows/executions")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Scheduled workflow execution reporting failed"
    }
