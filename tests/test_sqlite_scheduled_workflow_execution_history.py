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


def test_history_query_filters_by_state_before_pagination(tmp_path: Path):
    database = tmp_path / "workflow-filter.db"
    created_at = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
    store = SQLiteScheduledWorkflowExecutionStore(database)
    execution = store.create_or_get("occ-filter", created_at)
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

    filtered = store.get_history(
        execution.id,
        to_state="completed",
        limit=1,
    )

    assert [item[0] for item in filtered] == [3]
    assert filtered[0][2] == "completed"


def test_filtered_history_survives_store_restart(tmp_path: Path):
    database = tmp_path / "workflow-filter-restart.db"
    created_at = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
    store = SQLiteScheduledWorkflowExecutionStore(database)
    execution = store.create_or_get("occ-filter-restart", created_at)
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

    restarted = SQLiteScheduledWorkflowExecutionStore(database)
    filtered = restarted.get_history(execution.id, from_state="running")

    assert [item[0] for item in filtered] == [3]


def test_history_query_filters_by_utc_time_window(tmp_path: Path):
    database = tmp_path / "workflow-time-filter.db"
    store = SQLiteScheduledWorkflowExecutionStore(database)
    execution = store.create_or_get(
        "occ-time-filter",
        datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc),
    )
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

    filtered = store.get_history(
        execution.id,
        occurred_from=datetime(2026, 9, 19, 10, 1, tzinfo=timezone.utc),
        occurred_to=datetime(2026, 9, 19, 10, 2, tzinfo=timezone.utc),
    )

    assert [item[0] for item in filtered] == [2]
    assert filtered[0][3] == datetime(2026, 9, 19, 10, 1, tzinfo=timezone.utc)
