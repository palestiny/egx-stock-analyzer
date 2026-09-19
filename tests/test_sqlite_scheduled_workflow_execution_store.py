from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecutionState,
)
from app.infrastructure.persistence.sqlite_scheduled_workflow_execution_store import (
    ScheduledWorkflowExecutionConflictError,
    ScheduledWorkflowExecutionIdempotencyConflictError,
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

    first_running = first.start(now)
    store.save(first_running)
    store.save(first_running.interrupt(now))

    second_running = second.start(now)
    store.save(second_running)
    store.save(second_running.interrupt(now))

    completed_running = completed.start(now)
    store.save(completed_running)
    store.save(completed_running.complete(now))

    result = store.list_interrupted()

    assert [item.id for item in result] == [second.id, first.id]
    assert all(
        item.state is ScheduledWorkflowExecutionState.INTERRUPTED
        for item in result
    )


def test_existing_workflow_table_is_migrated_with_nullable_owner_column(tmp_path):
    database_path = tmp_path / "workflow.db"

    import sqlite3

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE scheduled_workflow_executions (
                execution_id TEXT PRIMARY KEY,
                occurrence_id TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                analysis_state TEXT NULL,
                delivery_state TEXT NULL
            )
            """
        )

    store = SQLiteScheduledWorkflowExecutionStore(database_path)
    execution = store.create_or_get(
        "legacy-occurrence",
        datetime(2026, 9, 19, 7, 0, tzinfo=timezone.utc),
    )

    assert execution.owner_user_id is None

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(scheduled_workflow_executions)"
            )
        }
    assert "owner_user_id" in columns


def test_same_key_and_fingerprint_is_idempotent(tmp_path):
    path = tmp_path / "workflow.db"
    first_store = SQLiteScheduledWorkflowExecutionStore(path)
    second_store = SQLiteScheduledWorkflowExecutionStore(path)
    now = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)

    first = first_store.create_or_get("same-key", now, request_fingerprint="fingerprint")
    second = second_store.create_or_get(
        " same-key ",
        now,
        request_fingerprint="fingerprint",
    )

    assert second.id == first.id


def test_same_key_with_different_fingerprint_is_conflict(tmp_path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    now = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)

    store.create_or_get("same-key", now, request_fingerprint="one")

    with pytest.raises(ScheduledWorkflowExecutionIdempotencyConflictError):
        store.create_or_get("same-key", now, request_fingerprint="two")


def test_two_sqlite_connections_racing_same_key_create_one_execution(tmp_path):
    path = tmp_path / "workflow.db"
    SQLiteScheduledWorkflowExecutionStore(path)
    now = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)

    def reserve():
        store = SQLiteScheduledWorkflowExecutionStore(path)
        return store.create_or_get("racing-key", now, request_fingerprint="same").id

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda _: reserve(), range(2)))

    assert ids[0] == ids[1]


def test_history_records_created_running_and_completed_in_sequence(tmp_path):
    path = tmp_path / "workflow.db"
    store = SQLiteScheduledWorkflowExecutionStore(path)
    now = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)

    created = store.create_or_get("history-key", now)
    running = created.start(datetime(2026, 9, 19, 8, 1, tzinfo=timezone.utc))
    store.save(running)
    completed = running.complete(datetime(2026, 9, 19, 8, 2, tzinfo=timezone.utc))
    store.save(completed)

    history = store.get_history(completed.id)

    assert [(item[0], item[2]) for item in history] == [
        (1, "created"),
        (2, "running"),
        (3, "completed"),
    ]
    assert history[1][1] == "created"
    assert history[2][1] == "running"


def test_stale_revision_cannot_overwrite_newer_state(tmp_path):
    path = tmp_path / "workflow.db"
    first_store = SQLiteScheduledWorkflowExecutionStore(path)
    second_store = SQLiteScheduledWorkflowExecutionStore(path)
    now = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)

    created = first_store.create_or_get("revision-key", now)
    stale = second_store.get(created.id)
    assert stale is not None

    current = created.start(datetime(2026, 9, 19, 8, 1, tzinfo=timezone.utc))
    first_store.save(current)

    with pytest.raises(ScheduledWorkflowExecutionConflictError):
        second_store.save(stale.start(datetime(2026, 9, 19, 8, 2, tzinfo=timezone.utc)))

    restored = first_store.get(created.id)
    assert restored is not None
    assert restored.state is ScheduledWorkflowExecutionState.RUNNING
    assert restored.revision == 1


def test_repeated_save_of_same_revision_is_idempotent(tmp_path):
    path = tmp_path / "workflow.db"
    store = SQLiteScheduledWorkflowExecutionStore(path)
    now = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)

    created = store.create_or_get("replay-key", now)
    running = created.start(datetime(2026, 9, 19, 8, 1, tzinfo=timezone.utc))
    store.save(running)
    store.save(running)

    assert len(store.get_history(running.id)) == 2


def test_history_write_failure_rolls_back_current_state(tmp_path, monkeypatch):
    path = tmp_path / "workflow.db"
    store = SQLiteScheduledWorkflowExecutionStore(path)
    now = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)
    created = store.create_or_get("atomic-key", now)
    running = created.start(datetime(2026, 9, 19, 8, 1, tzinfo=timezone.utc))

    def fail_history(connection, execution_id):
        raise RuntimeError("history failure")

    monkeypatch.setattr(
        SQLiteScheduledWorkflowExecutionStore,
        "_next_history_sequence",
        staticmethod(fail_history),
    )

    with pytest.raises(RuntimeError, match="history failure"):
        store.save(running)

    restored = store.get(created.id)
    assert restored is not None
    assert restored.state is ScheduledWorkflowExecutionState.CREATED
    assert restored.revision == 0
    assert len(store.get_history(created.id)) == 1
