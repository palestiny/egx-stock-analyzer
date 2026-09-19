from datetime import datetime, timezone
import pytest

from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecutionState,
)
from app.infrastructure.persistence.sqlite_scheduled_workflow_execution_store import (
    SQLiteScheduledWorkflowExecutionStore,
)


def test_create_is_idempotent_by_occurrence(tmp_path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    now = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)

    first = store.create_or_get("schedule-2026-09-19", now)
    second = store.create_or_get("schedule-2026-09-19", now)

    assert first.id == second.id
    assert first.state is ScheduledWorkflowExecutionState.CREATED


def test_lifecycle_transitions_survive_store_recreation(tmp_path):
    path = tmp_path / "workflow.db"
    store = SQLiteScheduledWorkflowExecutionStore(path)
    created = store.create_or_get(
        "schedule-2026-09-19",
        datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc),
    )

    running = created.start(datetime(2026, 9, 19, 8, 1, tzinfo=timezone.utc))
    store.save(running)
    completed = running.complete(
        datetime(2026, 9, 19, 8, 2, tzinfo=timezone.utc)
    )
    store.save(completed)

    restored = SQLiteScheduledWorkflowExecutionStore(path).get(completed.id)

    assert restored == completed


def test_invalid_transition_is_rejected(tmp_path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    execution = store.create_or_get(
        "occurrence",
        datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="must be running"):
        execution.complete(datetime(2026, 9, 19, 8, 1, tzinfo=timezone.utc))


def test_terminal_execution_cannot_restart(tmp_path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    created = store.create_or_get(
        "occurrence",
        datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc),
    )
    completed = created.start(
        datetime(2026, 9, 19, 8, 1, tzinfo=timezone.utc)
    ).complete(datetime(2026, 9, 19, 8, 2, tzinfo=timezone.utc))

    with pytest.raises(ValueError, match="must be created"):
        completed.start(datetime(2026, 9, 19, 8, 3, tzinfo=timezone.utc))


def test_recovery_marks_running_executions_interrupted(tmp_path):
    path = tmp_path / "workflow.db"
    store = SQLiteScheduledWorkflowExecutionStore(path)
    created = store.create_or_get(
        "occurrence",
        datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc),
    )
    store.save(created.start(datetime(2026, 9, 19, 8, 1, tzinfo=timezone.utc)))

    recovered = store.recover_running(
        datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc)
    )

    assert len(recovered) == 1
    assert recovered[0].id == created.id
    assert recovered[0].state is ScheduledWorkflowExecutionState.INTERRUPTED
    assert store.get(created.id).state is ScheduledWorkflowExecutionState.INTERRUPTED


def test_recovery_does_not_resume_execution(tmp_path):
    path = tmp_path / "workflow.db"
    store = SQLiteScheduledWorkflowExecutionStore(path)
    created = store.create_or_get(
        "occurrence",
        datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc,
    )
    )
    store.save(created.start(datetime(2026, 9, 19, 8, 1, tzinfo=timezone.utc)))

    store.recover_running(datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc))

    assert store.get(created.id).state is ScheduledWorkflowExecutionState.INTERRUPTED
