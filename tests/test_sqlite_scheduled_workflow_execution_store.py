from datetime import datetime, timezone

from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecutionState,
)
from app.infrastructure.persistence.sqlite_scheduled_workflow_execution_store import (
    SQLiteScheduledWorkflowExecutionStore,
)


def test_list_interrupted_returns_only_interrupted_in_deterministic_order(tmp_path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    now = datetime(2026, 9, 19, 7, 0, tzinfo=timezone.utc)

    first = store.create_or_get(
        "00000000-0000-0000-0000-000000000002:2026-09-19:08:30:00",
        now,
    )
    second = store.create_or_get(
        "00000000-0000-0000-0000-000000000001:2026-09-18:08:30:00",
        now,
    )
    completed = store.create_or_get(
        "00000000-0000-0000-0000-000000000003:2026-09-20:08:30:00",
        now,
    )

    store.save(first.start(now).interrupt(now))
    store.save(second.start(now).interrupt(now))
    store.save(completed.start(now).complete(now))

    result = store.list_interrupted()

    assert [item.id for item in result] == [second.id, first.id]
    assert all(
        item.state is ScheduledWorkflowExecutionState.INTERRUPTED
        for item in result
    )
