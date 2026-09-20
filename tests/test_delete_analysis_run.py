from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.application.analysis.delete_analysis_run import (
    DeleteAnalysisRun,
    AnalysisLifecycleNotFoundError,
)
from app.application.analysis.lifecycle_store import (
    AnalysisLifecycleStore,
)
from app.application.security.authorization import AuthorizationError
from app.application.security.identity import AuthenticatedIdentity
from app.application.analysis.run_store import InMemoryAnalysisRunStore
from app.domain.analysis_run import AnalysisRun
from app.domain.execution import ExecutionState


class FakeLifecycleStore(AnalysisLifecycleStore):
    def __init__(self) -> None:
        self.deleted_runs: list[tuple] = []
        self.deleted_snapshots: list[tuple] = []

    def delete_run(self, run_id, actor_user_id, target_user_id):
        self.deleted_runs.append((run_id, actor_user_id, target_user_id))
        return True

    def delete_snapshot(self, snapshot_id, actor_user_id, target_user_id):
        self.deleted_snapshots.append((snapshot_id, actor_user_id, target_user_id))
        return True


def make_run(owner_user_id):
    return AnalysisRun(
        id=uuid4(),
        created_at=datetime.now(timezone.utc),
        state=ExecutionState.COMPLETED,
        owner_user_id=owner_user_id,
    )


def test_delete_owned_run_delegates_to_lifecycle_store():
    owner = uuid4()
    run = make_run(owner)
    run_store = InMemoryAnalysisRunStore()
    run_store.save(run)
    lifecycle_store = FakeLifecycleStore()

    service = DeleteAnalysisRun(run_store, lifecycle_store)

    result = service.execute(run.id, AuthenticatedIdentity.user(owner))

    assert result.deleted is True
    assert lifecycle_store.deleted_runs == [(run.id, owner, owner)]


def test_delete_other_users_run_is_rejected():
    owner = uuid4()
    actor = uuid4()
    run = make_run(owner)
    run_store = InMemoryAnalysisRunStore()
    run_store.save(run)
    lifecycle_store = FakeLifecycleStore()

    service = DeleteAnalysisRun(run_store, lifecycle_store)

    with pytest.raises(AuthorizationError):
        service.execute(run.id, AuthenticatedIdentity.user(actor))

    assert lifecycle_store.deleted_runs == []


def test_delete_missing_run_raises_not_found():
    lifecycle_store = FakeLifecycleStore()
    service = DeleteAnalysisRun(InMemoryAnalysisRunStore(), lifecycle_store)

    with pytest.raises(AnalysisLifecycleNotFoundError):
        service.execute(uuid4(), AuthenticatedIdentity.user(uuid4()))


def test_operator_can_delete_global_run():
    run = make_run(None)
    run_store = InMemoryAnalysisRunStore()
    run_store.save(run)
    lifecycle_store = FakeLifecycleStore()

    service = DeleteAnalysisRun(run_store, lifecycle_store)

    result = service.execute(run.id, AuthenticatedIdentity.operator())

    assert result.deleted is True
    assert lifecycle_store.deleted_runs[0][0] == run.id
    assert lifecycle_store.deleted_runs[0][2] is None
