import sqlite3
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.analysis.lifecycle_store import PurgeStoreResult
from app.application.analysis.purge_analysis_lifecycle import PurgeAnalysisLifecycle
from app.application.security.authorization import AuthorizationError
from app.application.security.identity import AuthenticatedIdentity
from app.infrastructure.persistence.sqlite_analysis_lifecycle_store import (
    SQLiteAnalysisLifecycleStore,
)
from app.infrastructure.persistence.sqlite_analysis_result_store import SQLiteAnalysisResultStore
from app.infrastructure.persistence.sqlite_analysis_run_store import SQLiteAnalysisRunStore
from app.infrastructure.persistence.sqlite_management_audit_store import SQLiteManagementAuditStore


def _stores(database):
    SQLiteAnalysisRunStore(database)
    SQLiteAnalysisResultStore(database)
    SQLiteManagementAuditStore(database)
    return SQLiteAnalysisLifecycleStore(database)


def _insert_deleted_run(database, run_id=None, *, owner=None):
    run_id = run_id or uuid4()
    deleted_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO analysis_runs(
                run_id, created_at, state, owner_user_id, outcomes_available, deleted_at
            )
            VALUES (?, ?, 'completed', ?, 1, ?)
            """,
            (str(run_id), deleted_at, str(owner) if owner else None, deleted_at),
        )
        connection.execute(
            """
            INSERT INTO analysis_run_outcomes(
                run_id, symbol, state, stock_id, failure_code, failure_detail
            )
            VALUES (?, 'EGAL', 'success', NULL, NULL, NULL)
            """,
            (str(run_id),),
        )
    return run_id


def _insert_deleted_run_snapshot(database, run_id, snapshot_id=None):
    snapshot_id = snapshot_id or uuid4()
    deleted_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO analysis_results(
                snapshot_id, symbol, analysis_date, payload,
                analysis_run_id, owner_user_id, deleted_at
            )
            VALUES (?, 'EGAL', NULL, '{}', ?, NULL, ?)
            """,
            (str(snapshot_id), str(run_id), deleted_at),
        )
    return snapshot_id


def _insert_runless_deleted_snapshot(database, snapshot_id=None):
    snapshot_id = snapshot_id or uuid4()
    deleted_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO analysis_results(
                snapshot_id, symbol, analysis_date, payload,
                analysis_run_id, owner_user_id, deleted_at
            )
            VALUES (?, 'EGAL', NULL, '{}', NULL, NULL, ?)
            """,
            (str(snapshot_id), deleted_at),
        )
    return snapshot_id


def test_non_operator_cannot_purge():
    class FakeStore:
        def purge(self, **kwargs):
            raise AssertionError("purge must not be called")

    service = PurgeAnalysisLifecycle(FakeStore())

    with pytest.raises(AuthorizationError):
        service.execute(AuthenticatedIdentity.user(uuid4()))


def test_deleted_run_purge_removes_run_snapshot_and_outcome(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    actor = AuthenticatedIdentity.operator()
    run_id = _insert_deleted_run(database)
    snapshot_id = _insert_deleted_run_snapshot(database, run_id)

    result = PurgeAnalysisLifecycle(lifecycle).execute(
        actor,
        run_ids=(run_id,),
    )

    assert result.purged_run_ids == (run_id,)
    assert result.purged_snapshot_ids == ()

    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT 1 FROM analysis_runs WHERE run_id = ?", (str(run_id),)
        ).fetchone() is None
        assert connection.execute(
            "SELECT 1 FROM analysis_run_outcomes WHERE run_id = ?", (str(run_id),)
        ).fetchone() is None
        assert connection.execute(
            "SELECT 1 FROM analysis_results WHERE snapshot_id = ?", (str(snapshot_id),)
        ).fetchone() is None


def test_runless_snapshot_purge_removes_physical_row(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    snapshot_id = _insert_runless_deleted_snapshot(database)

    result = PurgeAnalysisLifecycle(lifecycle).execute(
        AuthenticatedIdentity.operator(),
        snapshot_ids=(snapshot_id,),
    )

    assert result.purged_snapshot_ids == (snapshot_id,)

    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT 1 FROM analysis_results WHERE snapshot_id = ?", (str(snapshot_id),)
        ).fetchone() is None


def test_visible_run_is_not_purgeable(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    run_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO analysis_runs(
                run_id, created_at, state, owner_user_id, outcomes_available, deleted_at
            )
            VALUES (?, ?, 'completed', NULL, 0, NULL)
            """,
            (str(run_id), now),
        )

    result = PurgeAnalysisLifecycle(lifecycle).execute(
        AuthenticatedIdentity.operator(),
        run_ids=(run_id,),
    )

    assert result.purged_run_ids == ()
    assert result.blocked_resource_ids == (run_id,)


def test_active_run_is_not_purgeable(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    run_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO analysis_runs(
                run_id, created_at, state, owner_user_id, outcomes_available, deleted_at
            )
            VALUES (?, ?, 'running', NULL, 0, ?)
            """,
            (str(run_id), now, now),
        )

    result = PurgeAnalysisLifecycle(lifecycle).execute(
        AuthenticatedIdentity.operator(),
        run_ids=(run_id,),
    )

    assert result.purged_run_ids == ()
    assert result.blocked_resource_ids == (run_id,)


def test_dry_run_does_not_delete_or_write_destructive_audit(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    run_id = _insert_deleted_run(database)

    result = PurgeAnalysisLifecycle(lifecycle).execute(
        AuthenticatedIdentity.operator(),
        run_ids=(run_id,),
        dry_run=True,
    )

    assert result.dry_run is True
    assert result.purged_run_ids == ()
    assert result.eligible_run_ids == (run_id,)

    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT 1 FROM analysis_runs WHERE run_id = ?", (str(run_id),)
        ).fetchone() is not None
        assert connection.execute(
            "SELECT COUNT(*) FROM management_audit WHERE action LIKE 'analysis_lifecycle.purge:%'"
        ).fetchone()[0] == 1


def test_purge_is_idempotent_on_repeat(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    run_id = _insert_deleted_run(database)

    first = PurgeAnalysisLifecycle(lifecycle).execute(
        AuthenticatedIdentity.operator(),
        run_ids=(run_id,),
    )
    second = PurgeAnalysisLifecycle(lifecycle).execute(
        AuthenticatedIdentity.operator(),
        run_ids=(run_id,),
    )

    assert first.purged_run_ids == (run_id,)
    assert second.purged_run_ids == ()
    assert second.failure_resource_id is None


def test_automatic_selection_is_stable_and_bounded(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    run_ids = sorted((_insert_deleted_run(database) for _ in range(3)), key=str)

    result = PurgeAnalysisLifecycle(lifecycle).execute(
        AuthenticatedIdentity.operator(),
        limit=2,
    )

    assert result.purged_run_ids == tuple(run_ids[:2])
    with sqlite3.connect(database) as connection:
        remaining = {
            UUID(row[0])
            for row in connection.execute("SELECT run_id FROM analysis_runs")
        }
    assert run_ids[2] in remaining


def test_purge_result_operation_id_matches_audit_operation(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    run_id = _insert_deleted_run(database)

    result = PurgeAnalysisLifecycle(lifecycle).execute(
        AuthenticatedIdentity.operator(),
        run_ids=(run_id,),
    )

    with sqlite3.connect(database) as connection:
        action = connection.execute(
            "SELECT action FROM management_audit WHERE action LIKE 'analysis_lifecycle.purge:%' ORDER BY id DESC LIMIT 1"
        ).fetchone()[0]

    assert action == f"analysis_lifecycle.purge:{result.operation_id}"


def test_automatic_selection_orders_runs_and_runless_snapshots_by_stable_id(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    run_id = UUID("00000000-0000-0000-0000-000000000002")
    snapshot_id = UUID("00000000-0000-0000-0000-000000000001")
    _insert_deleted_run(database, run_id)
    _insert_runless_deleted_snapshot(database, snapshot_id)

    result = PurgeAnalysisLifecycle(lifecycle).execute(
        AuthenticatedIdentity.operator(),
        limit=1,
    )

    assert result.purged_run_ids == ()
    assert result.purged_snapshot_ids == (snapshot_id,)
