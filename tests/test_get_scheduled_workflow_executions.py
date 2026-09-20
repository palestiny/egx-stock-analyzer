from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest
from uuid import uuid4

from app.application.security.identity import AuthenticatedIdentity
from app.application.execution.get_scheduled_workflow_executions import (
    GetScheduledWorkflowExecutions,
)
from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionState,
)
from app.infrastructure.persistence.sqlite_scheduled_workflow_execution_store import (
    SQLiteScheduledWorkflowExecutionStore,
)


def make_execution(occurrence_id: str, created_at: datetime, state=ScheduledWorkflowExecutionState.COMPLETED):
    return ScheduledWorkflowExecution(
        id=uuid4(),
        occurrence_id=occurrence_id,
        state=state,
        created_at=created_at,
        updated_at=created_at,
        analysis_state="completed",
        delivery_state="completed",
    )


def test_empty_history_returns_empty_collection(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    query = GetScheduledWorkflowExecutions(store)

    result = query.execute()

    assert result == ()


def test_returns_all_executions_newest_first(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    first = make_execution("occ-1", datetime(2026, 9, 18, 9, 0, tzinfo=timezone.utc))
    second = make_execution("occ-2", datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc))
    store.create_or_get(first.occurrence_id, first.created_at)
    store.create_or_get(second.occurrence_id, second.created_at)
    stored_first = store.get_by_occurrence(first.occurrence_id)
    stored_second = store.get_by_occurrence(second.occurrence_id)
    assert stored_first is not None
    assert stored_second is not None
    query = GetScheduledWorkflowExecutions(store)

    result = query.execute()

    assert [item.occurrence_id for item in result] == ["occ-2", "occ-1"]


def test_one_persisted_execution_is_projected_without_mutation(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    execution = make_execution(
        "occ-1",
        datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc),
    )
    stored = store.create_or_get(execution.occurrence_id, execution.created_at)
    before = store.get(stored.id)

    result = GetScheduledWorkflowExecutions(store).execute()
    after = store.get(stored.id)

    assert len(result) == 1
    assert result[0].id == stored.id
    assert after == before


def test_preserves_lifecycle_and_outcome_fields(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    execution = make_execution(
        "occ-1",
        datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc),
        ScheduledWorkflowExecutionState.INTERRUPTED,
    )
    stored = store.create_or_get(execution.occurrence_id, execution.created_at)
    assert stored is not None
    running = stored.start(execution.updated_at)
    store.save(running)
    interrupted = running.interrupt(execution.updated_at)
    store.save(
        replace(
            interrupted,
            analysis_state=execution.analysis_state,
            delivery_state=execution.delivery_state,
        )
    )

    result = GetScheduledWorkflowExecutions(store).execute()

    item = result[0]
    assert item.id == stored.id
    assert item.occurrence_id == "occ-1"
    assert item.state is ScheduledWorkflowExecutionState.INTERRUPTED
    assert item.created_at == execution.created_at
    assert item.updated_at == execution.updated_at
    assert item.analysis_state == "completed"
    assert item.delivery_state == "completed"


def test_occurrence_filter_returns_matching_execution_only(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    for occurrence_id in ("occ-1", "occ-2"):
        execution = make_execution(
            occurrence_id,
            datetime(2026, 9, 19, 9 if occurrence_id == "occ-1" else 10, 0, tzinfo=timezone.utc),
        )
        store.create_or_get(occurrence_id, execution.created_at)

    result = GetScheduledWorkflowExecutions(store).execute(occurrence_id="occ-2")

    assert [item.occurrence_id for item in result] == ["occ-2"]


def test_non_matching_occurrence_returns_empty_collection(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")

    result = GetScheduledWorkflowExecutions(store).execute(occurrence_id="missing")

    assert result == ()


def test_store_failure_propagates(tmp_path: Path):
    class FailingStore:
        def list_all(self):
            raise RuntimeError("workflow store unavailable")

        def get_by_occurrence(self, occurrence_id):
            raise RuntimeError("workflow store unavailable")

    query = GetScheduledWorkflowExecutions(FailingStore())

    with pytest.raises(RuntimeError, match="workflow store unavailable"):
        query.execute()


def test_authenticated_user_sees_only_owned_executions(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    user_a = uuid4()
    user_b = uuid4()
    now = datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc)
    store.create_or_get("user-a", now, owner_user_id=user_a)
    store.create_or_get("user-b", now, owner_user_id=user_b)

    result = GetScheduledWorkflowExecutions(store).execute(
        identity=AuthenticatedIdentity.user(user_a),
    )

    assert [item.occurrence_id for item in result] == ["user-a"]


def test_authenticated_user_cannot_read_another_users_execution_by_occurrence(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    owner = uuid4()
    now = datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc)
    store.create_or_get("owned-by-other", now, owner_user_id=owner)

    from app.application.security.authorization import AuthorizationError

    with pytest.raises(AuthorizationError, match="another user"):
        GetScheduledWorkflowExecutions(store).execute(
            occurrence_id="owned-by-other",
            identity=AuthenticatedIdentity.user(uuid4()),
        )


def test_legacy_operator_can_read_global_executions(tmp_path: Path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    now = datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc)
    store.create_or_get("global", now)

    result = GetScheduledWorkflowExecutions(store).execute(
        identity=AuthenticatedIdentity.operator(),
    )

    assert [item.occurrence_id for item in result] == ["global"]
