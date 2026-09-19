from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.execution.get_scheduled_workflow_execution_history import (
    ScheduledWorkflowExecutionHistoryReadModel,
    ScheduledWorkflowExecutionHistoryItem,
    ScheduledWorkflowExecutionHistoryNotFoundError,
    InvalidScheduledWorkflowExecutionHistoryQueryError,
)
from app.application.security.authorization import AuthorizationError


class FakeHistoryQuery:
    def __init__(self, read_model=None, error=None):
        self.read_model = read_model
        self.error = error
        self.calls = []

    def execute(self, execution_id, identity, page_size=None, cursor=None):
        self.calls.append((execution_id, identity, page_size, cursor))
        if self.error is not None:
            raise self.error
        return self.read_model


def make_model():
    execution_id = uuid4()
    now = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
    return ScheduledWorkflowExecutionHistoryReadModel(
        execution_id=execution_id,
        occurrence_id="occ-45",
        history=(
            ScheduledWorkflowExecutionHistoryItem(
                sequence=1,
                from_state=None,
                to_state="created",
                occurred_at=now,
                reason=None,
            ),
            ScheduledWorkflowExecutionHistoryItem(
                sequence=2,
                from_state="created",
                to_state="running",
                occurred_at=now,
                reason="started",
            ),
        ),
    )


def test_returns_workflow_lifecycle_history():
    model = make_model()
    query = FakeHistoryQuery(model)
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_execution_history=query,
    )

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/workflows/executions/{model.execution_id}/history"
        )

    assert response.status_code == 200
    assert response.json() == {
        "execution_id": str(model.execution_id),
        "occurrence_id": "occ-45",
        "history": [
            {
                "sequence": 1,
                "from_state": None,
                "to_state": "created",
                "occurred_at": "2026-09-19T10:00:00Z",
                "reason": None,
            },
            {
                "sequence": 2,
                "from_state": "created",
                "to_state": "running",
                "occurred_at": "2026-09-19T10:00:00Z",
                "reason": "started",
            },
        ],
    }
    assert len(query.calls) == 1
    assert query.calls[0][2:] == (None, None)


def test_returns_empty_history_for_valid_execution_without_transitions():
    model = make_model()
    model = ScheduledWorkflowExecutionHistoryReadModel(
        execution_id=model.execution_id,
        occurrence_id=model.occurrence_id,
        history=(),
    )
    query = FakeHistoryQuery(model)
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_execution_history=query,
    )

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/workflows/executions/{model.execution_id}/history"
        )

    assert response.status_code == 200
    assert response.json()["history"] == []


def test_returns_404_for_unknown_execution():
    execution_id = uuid4()
    query = FakeHistoryQuery(
        error=ScheduledWorkflowExecutionHistoryNotFoundError(
            f"Unknown scheduled workflow execution: {execution_id}"
        )
    )
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_execution_history=query,
    )

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/workflows/executions/{execution_id}/history"
        )

    assert response.status_code == 404


def test_returns_403_for_unauthorized_execution():
    query = FakeHistoryQuery(error=AuthorizationError("Resource is owned by another user"))
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_execution_history=query,
    )

    with TestClient(app) as client:
        response = client.get(f"/api/v1/workflows/executions/{uuid4()}/history")

    assert response.status_code == 403


def test_returns_503_when_history_query_is_not_configured():
    app = create_app(InMemoryAnalysisResultStore())

    with TestClient(app) as client:
        response = client.get(f"/api/v1/workflows/executions/{uuid4()}/history")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Scheduled workflow execution history is not configured"
    }


def test_api_reads_history_from_real_sqlite_store(tmp_path):
    from datetime import datetime, timezone

    from app.application.execution.get_scheduled_workflow_execution_history import (
        GetScheduledWorkflowExecutionHistory,
    )
    from app.infrastructure.persistence.sqlite_scheduled_workflow_execution_store import (
        SQLiteScheduledWorkflowExecutionStore,
    )

    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    created_at = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
    execution = store.create_or_get("occ-real", created_at)
    running = store.start_if_created(
        execution.id,
        datetime(2026, 9, 19, 10, 1, tzinfo=timezone.utc),
    )
    assert running is not None
    store.save(
        running.complete(
            datetime(2026, 9, 19, 10, 2, tzinfo=timezone.utc),
            reason="finished",
        )
    )

    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_execution_history=GetScheduledWorkflowExecutionHistory(store),
    )

    with TestClient(app) as client:
        response = client.get(f"/api/v1/workflows/executions/{execution.id}/history")

    assert response.status_code == 200
    assert [item["sequence"] for item in response.json()["history"]] == [1, 2, 3]


def test_api_passes_history_pagination_parameters():
    model = make_model()
    query = FakeHistoryQuery(model)
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_execution_history=query,
    )

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/workflows/executions/{model.execution_id}/history?page_size=2&cursor=Mg"
        )

    assert response.status_code == 200
    assert query.calls[0][2:] == (2, "Mg")


def test_api_maps_invalid_history_query_to_400():
    query = FakeHistoryQuery(
        error=InvalidScheduledWorkflowExecutionHistoryQueryError(
            "page_size must be between 1 and 100"
        )
    )
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_execution_history=query,
    )

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/workflows/executions/{uuid4()}/history?page_size=101"
        )

    assert response.status_code == 400
