from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.execution.get_scheduled_workflow_history import (
    InvalidScheduledWorkflowHistoryQueryError,
    ScheduledWorkflowHistoryItem,
    ScheduledWorkflowHistoryReadModel,
)


class FakeQuery:
    def __init__(self, model=None, error=None):
        self.model = model
        self.error = error
        self.calls = []

    def execute(
        self,
        identity,
        page_size=None,
        cursor=None,
        from_state=None,
        to_state=None,
        occurred_from=None,
        occurred_to=None,
    ):
        self.calls.append(
            (
                identity,
                page_size,
                cursor,
                from_state,
                to_state,
                occurred_from,
                occurred_to,
            )
        )
        if self.error:
            raise self.error
        return self.model


def model():
    return ScheduledWorkflowHistoryReadModel(
        items=(
            ScheduledWorkflowHistoryItem(
                execution_id=uuid4(),
                occurrence_id="occ-1",
                sequence=3,
                from_state="running",
                to_state="completed",
                occurred_at=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
                reason="finished",
            ),
        ),
        has_more=True,
        next_cursor="cursor-1",
    )


def test_cross_execution_history_endpoint_returns_read_model():
    query = FakeQuery(model())
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_history=query,
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/workflows/history?page_size=10&to_state=completed")

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["occurrence_id"] == "occ-1"
    assert body["items"][0]["sequence"] == 3
    assert body["has_more"] is True
    assert body["next_cursor"] == "cursor-1"
    assert query.calls[0][1] == 10
    assert query.calls[0][4] == "completed"


def test_cross_execution_history_endpoint_maps_invalid_query_to_400():
    query = FakeQuery(
        error=InvalidScheduledWorkflowHistoryQueryError(
            "page_size must be between 1 and 100"
        )
    )
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_history=query,
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/workflows/history?page_size=101")

    assert response.status_code == 400


def test_cross_execution_history_endpoint_returns_503_when_not_configured():
    app = create_app(InMemoryAnalysisResultStore())

    with TestClient(app) as client:
        response = client.get("/api/v1/workflows/history")

    assert response.status_code == 503
