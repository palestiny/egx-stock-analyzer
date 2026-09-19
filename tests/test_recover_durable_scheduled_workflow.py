from datetime import date, datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.application.execution.recover_durable_scheduled_workflow import (
    RecoverDurableScheduledWorkflow,
    WorkflowExecutionNotFoundError,
    WorkflowExecutionNotRecoverableError,
)
from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionState,
)


class FakeClock:
    def __init__(self):
        self.current = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)
    def now(self):
        return self.current


class FakeStore:
    def __init__(self, execution):
        self.execution = execution
        self.saved = []
    def get(self, execution_id):
        return self.execution if self.execution and self.execution.id == execution_id else None
    def create_or_get(self, occurrence_id, now):
        return self.execution
    def save(self, execution):
        self.execution = execution
        self.saved.append(execution)
    def get_by_occurrence(self, occurrence_id): return None
    def recover_running(self, now): return ()


def interrupted_execution():
    created = ScheduledWorkflowExecution.create("occ-1", datetime(2026, 9, 19, 7, 0, tzinfo=timezone.utc))
    return created.start(datetime(2026, 9, 19, 7, 1, tzinfo=timezone.utc)).interrupt(datetime(2026, 9, 19, 7, 2, tzinfo=timezone.utc))


def make_result():
    analysis = Mock(state=Mock(value="completed"))
    return Mock(analysis_execution=analysis, delivery_result=None)


def test_interrupted_execution_is_recovered_with_same_identity():
    original = interrupted_execution()
    store = FakeStore(original)
    workflow = Mock()
    workflow.recover.return_value = original.start_recovery(datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)).complete(datetime(2026, 9, 19, 8, 1, tzinfo=timezone.utc))
    result = RecoverDurableScheduledWorkflow(workflow).execute(original.id, date(2026, 9, 19))
    assert result.id == original.id
    workflow.recover.assert_called_once_with(original.id, date(2026, 9, 19))


def test_missing_execution_is_rejected():
    workflow = Mock()
    workflow.recover.side_effect = ValueError("Unknown scheduled workflow execution: x")
    with pytest.raises(WorkflowExecutionNotFoundError):
        RecoverDurableScheduledWorkflow(workflow).execute(uuid4(), date(2026, 9, 19))


def test_terminal_execution_is_rejected():
    workflow = Mock()
    workflow.recover.side_effect = ValueError("Scheduled workflow execution is not interrupted: completed")
    with pytest.raises(WorkflowExecutionNotRecoverableError):
        RecoverDurableScheduledWorkflow(workflow).execute(uuid4(), date(2026, 9, 19))


def test_recovery_does_not_create_new_execution_identity():
    original = interrupted_execution()
    workflow = Mock()
    workflow.recover.return_value = original.start_recovery(datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)).complete(datetime(2026, 9, 19, 8, 1, tzinfo=timezone.utc))
    result = RecoverDurableScheduledWorkflow(workflow).execute(original.id, date(2026, 9, 19))
    assert result.id == original.id
