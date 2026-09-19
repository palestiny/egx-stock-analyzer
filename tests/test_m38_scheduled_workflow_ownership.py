import sqlite3
from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID

from app.infrastructure.persistence.sqlite_scheduled_workflow_execution_store import (
    SQLiteScheduledWorkflowExecutionStore,
)


USER_A = UUID("00000000-0000-0000-0000-00000000000a")
USER_B = UUID("00000000-0000-0000-0000-00000000000b")
NOW = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)


def test_scheduled_workflow_owner_is_persisted_and_reloaded(tmp_path):
    path = tmp_path / "workflow.db"
    store = SQLiteScheduledWorkflowExecutionStore(path)

    created = store.create_or_get("user-a-occurrence", NOW, owner_user_id=USER_A)
    restored = SQLiteScheduledWorkflowExecutionStore(path).get(created.id)

    assert restored is not None
    assert restored.owner_user_id == USER_A


def test_legacy_scheduled_workflow_rows_are_migrated_as_global(tmp_path):
    path = tmp_path / "workflow.db"
    with sqlite3.connect(path) as connection:
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
        connection.execute(
            """
            INSERT INTO scheduled_workflow_executions
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "00000000-0000-0000-0000-000000000001",
                "legacy-occurrence",
                "completed",
                NOW.isoformat(),
                NOW.isoformat(),
                "completed",
                None,
            ),
        )

    store = SQLiteScheduledWorkflowExecutionStore(path)
    restored = store.get(UUID("00000000-0000-0000-0000-000000000001"))

    assert restored is not None
    assert restored.owner_user_id is None

    with sqlite3.connect(path) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(scheduled_workflow_executions)"
            )
        }

    assert "owner_user_id" in columns


def test_existing_occurrence_keeps_original_owner_for_idempotency(tmp_path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")

    first = store.create_or_get("same-occurrence", NOW, owner_user_id=USER_A)
    second = store.create_or_get("same-occurrence", NOW, owner_user_id=USER_B)

    assert second.id == first.id
    assert second.owner_user_id == USER_A


def test_owner_filter_returns_only_matching_user_owned_executions(tmp_path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")

    store.create_or_get("a", NOW, owner_user_id=USER_A)
    store.create_or_get("b", NOW, owner_user_id=USER_B)
    store.create_or_get("global", NOW)

    result = store.list_by_owner(USER_A)

    assert [item.occurrence_id for item in result] == ["a"]


def test_owner_is_immutable_when_lifecycle_state_is_saved(tmp_path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")

    created = store.create_or_get("owned", NOW, owner_user_id=USER_A)
    changed_owner = replace(created.start(NOW), owner_user_id=USER_B)
    store.save(changed_owner)

    restored = store.get(created.id)

    assert restored is not None
    assert restored.owner_user_id == USER_A
