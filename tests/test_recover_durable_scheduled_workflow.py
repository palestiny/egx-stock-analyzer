from datetime import date, datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.application.security.identity import AuthenticatedIdentity
from app.application.execution.recover_durable_scheduled_workflow import (
    RecoverDurableScheduledWorkflow,
    WorkflowExecutionNotFoundError,
    WorkflowExecutionNotRecoverableError,
)
from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionState,
)


class FakeStore:
    def __init__(self, execution=None):
        self.execution = execution

    def get(self, execution_id):
        if self.execution is not None and self.execution.id == execution_id:
            return self.execution
        return None


def interrupted_execution():
    created = ScheduledWorkflowExecution.create(
        "occ-1",
        datetime(2026, 9, 19, 7, 0, tzinfo=timezone.utc),
    )
    return created.start(
        datetime(2026, 9, 19, 7, 1, tzinfo=timezone.utc)
    ).interrupt(
        datetime(2026, 9, 19, 7, 2, tzinfo=timezone.utc)
    )


def test_interrupted_execution_is_recovered_with_same_identity():
    original = interrupted_execution()
    store = FakeStore(original)
    workflow = Mock()
    recovered = original.start_recovery(
        datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)
    ).complete(
        datetime(2026, 9, 19, 8, 1, tzinfo=timezone.utc)
    )
    workflow.recover.return_value = recovered

    result = RecoverDurableScheduledWorkflow(workflow, store).execute(
        original.id,
        date(2026, 9, 19),
    )

    assert result.id == original.id
    workflow.recover.assert_called_once_with(
        original.id,
        date(2026, 9, 19),
    )


def test_missing_execution_is_rejected():
    workflow = Mock()
    store = FakeStore()

    with pytest.raises(WorkflowExecutionNotFoundError):
        RecoverDurableScheduledWorkflow(workflow, store).execute(
            uuid4(),
            date(2026, 9, 19),
        )

    workflow.recover.assert_not_called()


def test_terminal_execution_is_rejected():
    created = ScheduledWorkflowExecution.create(
        "occ-1",
        datetime(2026, 9, 19, 7, 0, tzinfo=timezone.utc),
    )
    completed = created.start(
        datetime(2026, 9, 19, 7, 1, tzinfo=timezone.utc)
    ).complete(
        datetime(2026, 9, 19, 7, 2, tzinfo=timezone.utc)
    )
    workflow = Mock()
    store = FakeStore(completed)

    with pytest.raises(WorkflowExecutionNotRecoverableError):
        RecoverDurableScheduledWorkflow(workflow, store).execute(
            completed.id,
            date(2026, 9, 19),
        )

    workflow.recover.assert_not_called()


def test_recovery_does_not_create_new_execution_identity():
    original = interrupted_execution()
    store = FakeStore(original)
    workflow = Mock()
    recovered = original.start_recovery(
        datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)
    ).complete(
        datetime(2026, 9, 19, 8, 1, tzinfo=timezone.utc)
    )
    workflow.recover.return_value = recovered

    result = RecoverDurableScheduledWorkflow(workflow, store).execute(
        original.id,
        date(2026, 9, 19),
    )

    assert result.id == original.id
    assert result.state is ScheduledWorkflowExecutionState.COMPLETED


def test_user_can_recover_owned_execution():
    owner = uuid4()
    original = ScheduledWorkflowExecution.create(
        "owned",
        datetime(2026, 9, 19, 7, 0, tzinfo=timezone.utc),
        owner_user_id=owner,
    ).start(
        datetime(2026, 9, 19, 7, 1, tzinfo=timezone.utc)
    ).interrupt(
        datetime(2026, 9, 19, 7, 2, tzinfo=timezone.utc)
    )
    store = FakeStore(original)
    workflow = Mock()
    workflow.recover.return_value = original

    RecoverDurableScheduledWorkflow(workflow, store).execute(
        original.id,
        date(2026, 9, 19),
        AuthenticatedIdentity.user(owner),
    )

    workflow.recover.assert_called_once_with(
        original.id,
        date(2026, 9, 19),
        AuthenticatedIdentity.user(owner),
    )


def test_user_cannot_recover_another_users_execution():
    owner = uuid4()
    original = ScheduledWorkflowExecution.create(
        "owned",
        datetime(2026, 9, 19, 7, 0, tzinfo=timezone.utc),
        owner_user_id=owner,
    ).start(
        datetime(2026, 9, 19, 7, 1, tzinfo=timezone.utc)
    ).interrupt(
        datetime(2026, 9, 19, 7, 2, tzinfo=timezone.utc)
    )
    store = FakeStore(original)
    workflow = Mock()

    from app.application.security.authorization import AuthorizationError

    with pytest.raises(AuthorizationError, match="another user"):
        RecoverDurableScheduledWorkflow(workflow, store).execute(
            original.id,
            date(2026, 9, 19),
            AuthenticatedIdentity.user(uuid4()),
        )

    workflow.recover.assert_not_called()


def test_legacy_operator_can_recover_global_execution():
    original = interrupted_execution()
    store = FakeStore(original)
    workflow = Mock()
    workflow.recover.return_value = original

    RecoverDurableScheduledWorkflow(workflow, store).execute(
        original.id,
        date(2026, 9, 19),
        AuthenticatedIdentity.operator(),
    )

    workflow.recover.assert_called_once()
