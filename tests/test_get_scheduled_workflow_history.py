from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.application.execution.get_scheduled_workflow_history import (
    GetScheduledWorkflowHistory,
    InvalidScheduledWorkflowHistoryQueryError,
)
from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecutionState,
)
from app.application.security.identity import AuthenticatedIdentity
from app.domain.identity.user import UserStatus
from app.application.security.authorization import AuthorizationError


class FakeStore:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def get_cross_execution_history(
        self,
        owner_user_id,
        global_only,
        after_cursor=None,
        limit=None,
        from_state=None,
        to_state=None,
        occurred_from=None,
        occurred_to=None,
    ):
        self.calls.append(
            {
                "owner_user_id": owner_user_id,
                "global_only": global_only,
                "after_cursor": after_cursor,
                "limit": limit,
                "from_state": from_state,
                "to_state": to_state,
                "occurred_from": occurred_from,
                "occurred_to": occurred_to,
            }
        )
        return self.rows[:limit] if limit is not None else self.rows


def make_rows():
    first = uuid4()
    second = uuid4()
    now = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)
    return (
        (first, "occ-1", 2, "running", "completed", now, "done"),
        (second, "occ-2", 1, None, "created", now, None),
    )


def test_user_scope_is_passed_to_store():
    owner = uuid4()
    store = FakeStore(make_rows())

    result = GetScheduledWorkflowHistory(store).execute(
        AuthenticatedIdentity.user(owner),
        page_size=10,
    )

    assert len(result.items) == 2
    assert store.calls[0]["owner_user_id"] == owner
    assert store.calls[0]["global_only"] is False


def test_operator_scope_is_global_only():
    store = FakeStore(make_rows())

    GetScheduledWorkflowHistory(store).execute(
        AuthenticatedIdentity.operator(),
        page_size=10,
    )

    assert store.calls[0]["owner_user_id"] is None
    assert store.calls[0]["global_only"] is True


def test_state_and_time_filters_are_forwarded():
    store = FakeStore(make_rows())
    start = datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 20, 11, 0, tzinfo=timezone.utc)

    GetScheduledWorkflowHistory(store).execute(
        AuthenticatedIdentity.operator(),
        page_size=10,
        from_state="running",
        to_state="completed",
        occurred_from=start,
        occurred_to=end,
    )

    call = store.calls[0]
    assert call["from_state"] == "running"
    assert call["to_state"] == "completed"
    assert call["occurred_from"] == start
    assert call["occurred_to"] == end


def test_pagination_cursor_is_composite_and_continues():
    rows = tuple(
        (
            uuid4(),
            f"occ-{index}",
            1,
            "running",
            "completed",
            datetime(2026, 9, 20, 10, index, tzinfo=timezone.utc),
            None,
        )
        for index in range(1, 4)
    )
    store = FakeStore(rows)
    query = GetScheduledWorkflowHistory(store)

    first = query.execute(AuthenticatedIdentity.operator(), page_size=2)
    assert first.has_more is True
    assert first.next_cursor is not None

    second = query.execute(
        AuthenticatedIdentity.operator(),
        page_size=2,
        cursor=first.next_cursor,
    )

    assert second.has_more is False
    assert store.calls[1]["after_cursor"] is not None
    assert store.calls[1]["after_cursor"][2] == 1


def test_cursor_cannot_cross_filter_shape():
    store = FakeStore(make_rows())
    query = GetScheduledWorkflowHistory(store)

    first = query.execute(
        AuthenticatedIdentity.operator(),
        page_size=1,
        to_state="completed",
    )

    with pytest.raises(InvalidScheduledWorkflowHistoryQueryError, match="does not match"):
        query.execute(
            AuthenticatedIdentity.operator(),
            page_size=1,
            cursor=first.next_cursor,
            to_state="failed",
        )


@pytest.mark.parametrize("page_size", [0, 101])
def test_page_size_is_bounded(page_size):
    with pytest.raises(InvalidScheduledWorkflowHistoryQueryError, match="page_size"):
        GetScheduledWorkflowHistory(FakeStore(make_rows())).execute(
            AuthenticatedIdentity.operator(),
            page_size=page_size,
        )


def test_invalid_state_is_rejected():
    with pytest.raises(InvalidScheduledWorkflowHistoryQueryError, match="valid"):
        GetScheduledWorkflowHistory(FakeStore(make_rows())).execute(
            AuthenticatedIdentity.operator(),
            from_state="invalid",
        )


def test_disabled_user_cannot_query_cross_execution_history():
    with pytest.raises(AuthorizationError, match="not active"):
        GetScheduledWorkflowHistory(FakeStore(make_rows())).execute(
            AuthenticatedIdentity.user(uuid4(), status=UserStatus.DISABLED),
        )
