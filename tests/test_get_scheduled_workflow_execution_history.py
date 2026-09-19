from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.application.execution.get_scheduled_workflow_execution_history import (
    GetScheduledWorkflowExecutionHistory,
    ScheduledWorkflowExecutionHistoryNotFoundError,
)
from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionState,
)
from app.application.security.authorization import AuthorizationError
from app.application.security.identity import AuthenticatedIdentity


class FakeStore:
    def __init__(self, execution=None, history=()):
        self.execution = execution
        self.history = history
        self.history_calls = 0

    def get(self, execution_id):
        if self.execution is not None and self.execution.id == execution_id:
            return self.execution
        return None

    def get_history(self, execution_id):
        self.history_calls += 1
        return self.history


def make_execution(owner_user_id=None):
    now = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
    return ScheduledWorkflowExecution(
        id=uuid4(),
        occurrence_id="occ-45",
        state=ScheduledWorkflowExecutionState.COMPLETED,
        created_at=now,
        updated_at=now,
        owner_user_id=owner_user_id,
    )


def test_returns_persisted_history_in_sequence_order():
    execution = make_execution()
    history = (
        (1, None, "created", execution.created_at, None),
        (2, "created", "running", execution.updated_at, "started"),
        (3, "running", "completed", execution.updated_at, "finished"),
    )
    store = FakeStore(execution, history)

    result = GetScheduledWorkflowExecutionHistory(store).execute(
        execution.id,
        AuthenticatedIdentity.operator(),
    )

    assert result.execution_id == execution.id
    assert result.occurrence_id == "occ-45"
    assert [item.sequence for item in result.history] == [1, 2, 3]
    assert result.history[0].from_state is None
    assert result.history[1].reason == "started"
    assert result.history[2].to_state == "completed"


def test_valid_execution_with_no_history_returns_empty_collection():
    execution = make_execution()
    store = FakeStore(execution)

    result = GetScheduledWorkflowExecutionHistory(store).execute(
        execution.id,
        AuthenticatedIdentity.operator(),
    )

    assert result.history == ()
    assert store.history_calls == 1


def test_missing_execution_is_not_found():
    execution_id = uuid4()

    with pytest.raises(
        ScheduledWorkflowExecutionHistoryNotFoundError,
        match=str(execution_id),
    ):
        GetScheduledWorkflowExecutionHistory(FakeStore()).execute(
            execution_id,
            AuthenticatedIdentity.operator(),
        )


def test_user_can_read_owned_execution():
    owner = uuid4()
    execution = make_execution(owner)
    result = GetScheduledWorkflowExecutionHistory(
        FakeStore(execution)
    ).execute(
        execution.id,
        AuthenticatedIdentity.user(owner),
    )

    assert result.execution_id == execution.id


def test_user_cannot_read_another_users_execution():
    execution = make_execution(uuid4())

    with pytest.raises(AuthorizationError, match="another user"):
        GetScheduledWorkflowExecutionHistory(
            FakeStore(execution)
        ).execute(
            execution.id,
            AuthenticatedIdentity.user(uuid4()),
        )


def test_read_capability_does_not_mutate_execution():
    execution = make_execution()
    before = execution
    GetScheduledWorkflowExecutionHistory(FakeStore(execution)).execute(
        execution.id,
        AuthenticatedIdentity.operator(),
    )

    assert execution == before
