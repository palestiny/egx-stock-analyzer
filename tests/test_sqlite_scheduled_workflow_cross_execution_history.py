from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.application.execution.scheduled_workflow_execution import ScheduledWorkflowExecution
from app.infrastructure.persistence.sqlite_scheduled_workflow_execution_store import (
    SQLiteScheduledWorkflowExecutionStore,
)


def make_execution(occurrence_id, owner_user_id=None, when=None):
    when = when or datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)
    return ScheduledWorkflowExecution.create(
        occurrence_id,
        when,
        owner_user_id=owner_user_id,
    )


def persist_history(store, execution):
    stored = store.create_or_get(
        execution.occurrence_id,
        execution.created_at,
        owner_user_id=execution.owner_user_id,
    )
    running = stored.start(execution.updated_at)
    store.save(running)
    completed = running.complete(
        execution.updated_at.replace(minute=execution.updated_at.minute + 1),
        reason="finished",
    )
    store.save(completed)
    return stored


def test_cross_execution_history_is_newest_first_and_bounded(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    first = persist_history(
        store,
        make_execution("occ-1", when=datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc)),
    )
    second = persist_history(
        store,
        make_execution("occ-2", when=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)),
    )

    rows = store.get_cross_execution_history(
        owner_user_id=None,
        global_only=True,
        limit=2,
    )

    assert len(rows) == 2
    assert rows[0][0] == second.id
    assert rows[1][0] == first.id


def test_cross_execution_history_is_isolated_by_owner(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    owner_a = uuid4()
    owner_b = uuid4()
    first = persist_history(store, make_execution("a", owner_a))
    second = persist_history(store, make_execution("b", owner_b))

    rows = store.get_cross_execution_history(
        owner_user_id=owner_a,
        global_only=False,
    )

    assert {row[0] for row in rows} == {first.id}
    assert second.id not in {row[0] for row in rows}


def test_cross_execution_history_keeps_global_scope_separate(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    global_execution = persist_history(store, make_execution("global"))
    user_execution = persist_history(store, make_execution("user", uuid4()))

    rows = store.get_cross_execution_history(
        owner_user_id=None,
        global_only=True,
    )

    assert {row[0] for row in rows} == {global_execution.id}
    assert user_execution.id not in {row[0] for row in rows}


def test_cross_execution_history_filters_before_pagination(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    execution = persist_history(store, make_execution("filtered"))

    rows = store.get_cross_execution_history(
        owner_user_id=None,
        global_only=True,
        to_state="completed",
        limit=10,
    )

    assert rows
    assert all(row[4] == "completed" for row in rows)
    assert all(row[0] == execution.id for row in rows)


def test_cross_execution_history_survives_store_restart(tmp_path: Path):
    database = tmp_path / "workflow.db"
    store = SQLiteScheduledWorkflowExecutionStore(database)
    execution = persist_history(
        store,
        make_execution("restart", when=datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)),
    )

    restarted = SQLiteScheduledWorkflowExecutionStore(database)
    rows = restarted.get_cross_execution_history(
        owner_user_id=None,
        global_only=True,
    )

    assert {row[0] for row in rows} == {execution.id}


def test_cross_execution_history_query_plan_is_available(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    with store._connect() as connection:
        plan = connection.execute(
            """
            EXPLAIN QUERY PLAN
            SELECT h.execution_id, e.occurrence_id, h.sequence,
                   h.from_state, h.to_state, h.occurred_at, h.reason
            FROM scheduled_workflow_execution_history AS h
            INNER JOIN scheduled_workflow_executions AS e
                ON e.execution_id = h.execution_id
            WHERE e.owner_user_id IS NULL
              AND h.to_state = ?
            ORDER BY h.occurred_at DESC, h.execution_id DESC, h.sequence DESC
            LIMIT ?
            """,
            ("completed", 51),
        ).fetchall()

    assert plan
    assert all(row[-1] for row in plan)
