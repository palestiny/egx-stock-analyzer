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

    def get_history(
        self,
        execution_id,
        after_sequence=None,
        limit=None,
        from_state=None,
        to_state=None,
    ):
        self.history_calls += 1
        rows = tuple(
            row for row in self.history
            if (after_sequence is None or row[0] > after_sequence)
            and (from_state is None or row[1] == from_state)
            and (to_state is None or row[2] == to_state)
        )
        return rows if limit is None else rows[:limit]


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


def test_bounded_query_returns_first_page_and_cursor():
    execution = make_execution()
    history = tuple(
        (sequence, "running", "running", execution.updated_at, None)
        for sequence in range(1, 4)
    )
    result = GetScheduledWorkflowExecutionHistory(FakeStore(execution, history)).execute(
        execution.id,
        AuthenticatedIdentity.operator(),
        page_size=2,
    )

    assert [item.sequence for item in result.history] == [1, 2]
    assert result.has_more is True
    assert result.next_cursor is not None


def test_cursor_continues_after_last_returned_sequence():
    execution = make_execution()
    history = tuple(
        (sequence, "running", "running", execution.updated_at, None)
        for sequence in range(1, 4)
    )
    query = GetScheduledWorkflowExecutionHistory(FakeStore(execution, history))

    first = query.execute(execution.id, AuthenticatedIdentity.operator(), page_size=2)
    second = query.execute(
        execution.id,
        AuthenticatedIdentity.operator(),
        page_size=2,
        cursor=first.next_cursor,
    )

    assert [item.sequence for item in second.history] == [3]
    assert second.has_more is False
    assert second.next_cursor is None


@pytest.mark.parametrize("page_size", [0, -1, 101])
def test_invalid_page_size_is_rejected(page_size):
    execution = make_execution()

    with pytest.raises(ValueError, match="page_size"):
        GetScheduledWorkflowExecutionHistory(FakeStore(execution)).execute(
            execution.id,
            AuthenticatedIdentity.operator(),
            page_size=page_size,
        )


@pytest.mark.parametrize("cursor", ["", "invalid", "MA=="])
def test_invalid_cursor_is_rejected(cursor):
    execution = make_execution()

    with pytest.raises(ValueError, match="cursor"):
        GetScheduledWorkflowExecutionHistory(FakeStore(execution)).execute(
            execution.id,
            AuthenticatedIdentity.operator(),
            page_size=2,
            cursor=cursor,
        )


def test_legacy_query_without_pagination_returns_complete_history():
    execution = make_execution()
    history = tuple(
        (sequence, "running", "running", execution.updated_at, None)
        for sequence in range(1, 4)
    )

    result = GetScheduledWorkflowExecutionHistory(FakeStore(execution, history)).execute(
        execution.id,
        AuthenticatedIdentity.operator(),
    )

    assert [item.sequence for item in result.history] == [1, 2, 3]
    assert result.has_more is False
    assert result.next_cursor is None


def test_filters_by_to_state():
    execution = make_execution()
    history = (
        (1, None, "created", execution.updated_at, None),
        (2, "created", "running", execution.updated_at, None),
        (3, "running", "completed", execution.updated_at, None),
        (4, "completed", "interrupted", execution.updated_at, None),
    )

    result = GetScheduledWorkflowExecutionHistory(FakeStore(execution, history)).execute(
        execution.id,
        AuthenticatedIdentity.operator(),
        to_state="completed",
    )

    assert [item.sequence for item in result.history] == [3]


def test_filters_by_from_state():
    execution = make_execution()
    history = (
        (1, None, "created", execution.updated_at, None),
        (2, "created", "running", execution.updated_at, None),
        (3, "running", "completed", execution.updated_at, None),
    )

    result = GetScheduledWorkflowExecutionHistory(FakeStore(execution, history)).execute(
        execution.id,
        AuthenticatedIdentity.operator(),
        from_state="running",
    )

    assert [item.sequence for item in result.history] == [3]


def test_combined_filters_match_exact_transition():
    execution = make_execution()
    history = (
        (1, None, "created", execution.updated_at, None),
        (2, "created", "running", execution.updated_at, None),
        (3, "running", "completed", execution.updated_at, None),
        (4, "running", "failed", execution.updated_at, None),
    )

    result = GetScheduledWorkflowExecutionHistory(FakeStore(execution, history)).execute(
        execution.id,
        AuthenticatedIdentity.operator(),
        from_state="running",
        to_state="completed",
    )

    assert [item.sequence for item in result.history] == [3]


@pytest.mark.parametrize("parameter", ["from_state", "to_state"])
def test_invalid_state_filter_is_rejected(parameter):
    execution = make_execution()

    with pytest.raises(ValueError, match="valid scheduled workflow execution state"):
        GetScheduledWorkflowExecutionHistory(FakeStore(execution)).execute(
            execution.id,
            AuthenticatedIdentity.operator(),
            **{parameter: "not-a-state"},
        )


def test_filter_matching_no_history_returns_empty_collection():
    execution = make_execution()
    history = ((1, None, "created", execution.updated_at, None),)

    result = GetScheduledWorkflowExecutionHistory(FakeStore(execution, history)).execute(
        execution.id,
        AuthenticatedIdentity.operator(),
        to_state="completed",
    )

    assert result.history == ()


def test_filtered_pagination_uses_filtered_sequence_and_cursor():
    execution = make_execution()
    history = tuple(
        (sequence, "running", "completed" if sequence % 2 else "failed", execution.updated_at, None)
        for sequence in range(1, 6)
    )
    query = GetScheduledWorkflowExecutionHistory(FakeStore(execution, history))

    first = query.execute(
        execution.id,
        AuthenticatedIdentity.operator(),
        page_size=1,
        to_state="completed",
    )
    second = query.execute(
        execution.id,
        AuthenticatedIdentity.operator(),
        page_size=1,
        cursor=first.next_cursor,
        to_state="completed",
    )

    assert [item.sequence for item in first.history] == [1]
    assert [item.sequence for item in second.history] == [3]


def test_filtered_cursor_cannot_be_reused_with_different_filter():
    execution = make_execution()
    history = (
        (1, "running", "completed", execution.updated_at, None),
        (2, "running", "completed", execution.updated_at, None),
        (3, "running", "failed", execution.updated_at, None),
    )
    query = GetScheduledWorkflowExecutionHistory(FakeStore(execution, history))

    first = query.execute(
        execution.id,
        AuthenticatedIdentity.operator(),
        page_size=1,
        to_state="completed",
    )

    with pytest.raises(ValueError, match="does not match"):
        query.execute(
            execution.id,
            AuthenticatedIdentity.operator(),
            page_size=1,
            cursor=first.next_cursor,
            to_state="failed",
        )
