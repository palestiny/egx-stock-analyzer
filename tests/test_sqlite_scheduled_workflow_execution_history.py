from datetime import datetime, timezone
from pathlib import Path

from app.infrastructure.persistence.sqlite_scheduled_workflow_execution_store import (
    SQLiteScheduledWorkflowExecutionStore,
)


def test_history_survives_store_restart_and_preserves_sequence(tmp_path: Path):
    database = tmp_path / "workflow.db"
    created_at = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
    running_at = datetime(2026, 9, 19, 10, 1, tzinfo=timezone.utc)
    completed_at = datetime(2026, 9, 19, 10, 2, tzinfo=timezone.utc)

    first_store = SQLiteScheduledWorkflowExecutionStore(database)
    execution = first_store.create_or_get("occ-45", created_at)
    running = first_store.start_if_created(execution.id, running_at)
    assert running is not None
    completed = running.complete(completed_at, reason="finished")
    first_store.save(completed)

    restarted_store = SQLiteScheduledWorkflowExecutionStore(database)
    history = restarted_store.get_history(execution.id)

    assert [item[0] for item in history] == [1, 2, 3]
    assert history[0][1:] == (None, "created", created_at, None)
    assert history[1][1:] == ("created", "running", running_at, None)
    assert history[2][1:] == ("running", "completed", completed_at, "finished")


def test_missing_execution_has_empty_history(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")

    assert store.get_history(
        __import__("uuid").uuid4()
    ) == ()


def test_history_query_supports_sequence_cursor_and_limit(tmp_path: Path):
    database = tmp_path / "workflow.db"
    created_at = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
    store = SQLiteScheduledWorkflowExecutionStore(database)
    execution = store.create_or_get("occ-pagination", created_at)
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

    first = store.get_history(execution.id, limit=2)
    second = store.get_history(execution.id, after_sequence=first[-1][0], limit=2)

    assert [item[0] for item in first] == [1, 2]
    assert [item[0] for item in second] == [3]


def test_history_filters_before_limit(tmp_path: Path):
    database = tmp_path / "workflow.db"
    created_at = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
    store = SQLiteScheduledWorkflowExecutionStore(database)
    execution = store.create_or_get("occ-filter", created_at)
    running = store.start_if_created(
        execution.id,
        datetime(2026, 9, 19, 10, 1, tzinfo=timezone.utc),
    )
    assert running is not None
    failed = running.fail(
        datetime(2026, 9, 19, 10, 2, tzinfo=timezone.utc),
        reason="failed",
    )
    store.save(failed)
    interrupted = failed.interrupt(
        datetime(2026, 9, 19, 10, 3, tzinfo=timezone.utc),
        reason="interrupted",
    )
    store.save(interrupted)

    rows = store.get_history(
        execution.id,
        to_state="failed",
        limit=1,
    )

    assert [row[0] for row in rows] == [3]
    assert rows[0][2] == "failed"


def test_history_supports_exact_transition_filter(tmp_path: Path):
    database = tmp_path / "workflow.db"
    created_at = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
    store = SQLiteScheduledWorkflowExecutionStore(database)
    execution = store.create_or_get("occ-transition-filter", created_at)
    running = store.start_if_created(
        execution.id,
        datetime(2026, 9, 19, 10, 1, tzinfo=timezone.utc),
    )
    assert running is not None
    completed = running.complete(
        datetime(2026, 9, 19, 10, 2, tzinfo=timezone.utc),
        reason="finished",
    )
    store.save(completed)

    rows = store.get_history(
        execution.id,
        from_state="running",
        to_state="completed",
    )

    assert [row[0] for row in rows] == [3]
