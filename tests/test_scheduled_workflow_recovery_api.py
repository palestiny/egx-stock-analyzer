from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.execution.recover_durable_scheduled_workflow import (
    WorkflowExecutionNotFoundError,
    WorkflowExecutionNotRecoverableError,
)
from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionState,
)
from app.application.execution.result_store import AnalysisResultStore


def make_execution(state):
    now = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
    return ScheduledWorkflowExecution(
        id=uuid4(),
        occurrence_id="occurrence-1",
        state=state,
        created_at=now,
        updated_at=now,
    )


class FakeRecovery:
    def __init__(self, execution):
        self.execution = execution
        self.calls = []

    def execute(self, execution_id, as_of):
        self.calls.append((execution_id, as_of))
        return self.execution


class NullResultStore:
    def save(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        return None

    def get_record(self, *args, **kwargs):
        return None


def make_client(recovery):
    return TestClient(
        create_app(
            result_store=NullResultStore(),
            recover_durable_scheduled_workflow=recovery,
        )
    )


def test_recovery_endpoint_delegates_and_returns_execution():
    execution = make_execution(ScheduledWorkflowExecutionState.COMPLETED)
    recovery = FakeRecovery(execution)

    with make_client(recovery) as client:
        response = client.post(f"/api/v1/workflows/executions/{execution.id}/recover")

    assert response.status_code == 200
    assert response.json()["id"] == str(execution.id)
    assert response.json()["state"] == "completed"
    assert recovery.calls == [(execution.id, date.today())]


def test_recovery_endpoint_maps_missing_execution_to_404():
    class MissingRecovery:
        def execute(self, execution_id, as_of):
            raise WorkflowExecutionNotFoundError("Unknown scheduled workflow execution")

    with make_client(MissingRecovery()) as client:
        response = client.post(f"/api/v1/workflows/executions/{uuid4()}/recover")

    assert response.status_code == 404


def test_recovery_endpoint_maps_non_recoverable_execution_to_409():
    class NonRecoverableRecovery:
        def execute(self, execution_id, as_of):
            raise WorkflowExecutionNotRecoverableError("Scheduled workflow execution is not interrupted: completed")

    with make_client(NonRecoverableRecovery()) as client:
        response = client.post(f"/api/v1/workflows/executions/{uuid4()}/recover")

    assert response.status_code == 409


def test_recovery_endpoint_returns_503_when_not_configured():
    with TestClient(create_app(result_store=NullResultStore())) as client:
        response = client.post(f"/api/v1/workflows/executions/{uuid4()}/recover")

    assert response.status_code == 503
