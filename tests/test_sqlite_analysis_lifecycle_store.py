import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from app.application.analysis.lifecycle_store import LifecycleDeletionOutcome
from app.application.identity.management_audit import ManagementAuditQuery
from app.infrastructure.persistence.sqlite_analysis_lifecycle_store import (
    SQLiteAnalysisLifecycleStore,
)
from app.infrastructure.persistence.sqlite_analysis_run_store import SQLiteAnalysisRunStore
from app.infrastructure.persistence.sqlite_analysis_result_store import SQLiteAnalysisResultStore
from app.infrastructure.persistence.sqlite_management_audit_store import (
    SQLiteManagementAuditStore,
)


def test_run_delete_hides_run_and_correlated_snapshots_atomically(tmp_path):
    database = tmp_path / "analysis.db"
    run_store = SQLiteAnalysisRunStore(database)
    SQLiteAnalysisResultStore(database)
    audit_store = SQLiteManagementAuditStore(database)
    lifecycle = SQLiteAnalysisLifecycleStore(database)

    run_id = uuid4()
    actor = uuid4()
    snapshot_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO analysis_runs(run_id, created_at, state, owner_user_id, outcomes_available, deleted_at) VALUES (?, ?, ?, ?, ?, NULL)",
            (str(run_id), now, "completed", str(actor), 0),
        )
        connection.execute(
            "INSERT INTO analysis_results(snapshot_id, symbol, analysis_date, payload, analysis_run_id, owner_user_id, deleted_at) VALUES (?, ?, ?, ?, ?, ?, NULL)",
            (str(snapshot_id), "EGAL", None, "{}", str(run_id), str(actor)),
        )

    outcome = lifecycle.delete_run(run_id, actor, actor)

    assert outcome is LifecycleDeletionOutcome.DELETED
    assert run_store.get(run_id) is None

    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT deleted_at FROM analysis_results WHERE snapshot_id = ?",
            (str(snapshot_id),),
        ).fetchone()[0] is not None

    events = audit_store.read_page(ManagementAuditQuery(action="analysis_run.delete"), offset=0, limit=10)
    assert events.total_count == 1
    assert events.items[0].event.outcome == "deleted"


def test_repeated_run_delete_is_idempotent_and_audited(tmp_path):
    database = tmp_path / "analysis.db"
    SQLiteAnalysisRunStore(database)
    SQLiteAnalysisResultStore(database)
    SQLiteManagementAuditStore(database)
    lifecycle = SQLiteAnalysisLifecycleStore(database)

    run_id = uuid4()
    actor = uuid4()
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO analysis_runs(run_id, created_at, state, owner_user_id, outcomes_available, deleted_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(run_id), now, "completed", str(actor), 0, now),
        )

    assert lifecycle.delete_run(run_id, actor, actor) is LifecycleDeletionOutcome.NOOP
    with sqlite3.connect(database) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM management_audit WHERE action = 'analysis_run.delete'"
        ).fetchone()[0]
    assert count == 1


def test_active_run_delete_is_rejected_without_mutation(tmp_path):
    database = tmp_path / "analysis.db"
    SQLiteAnalysisRunStore(database)
    SQLiteManagementAuditStore(database)
    lifecycle = SQLiteAnalysisLifecycleStore(database)

    run_id = uuid4()
    actor = uuid4()
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO analysis_runs(run_id, created_at, state, owner_user_id, outcomes_available, deleted_at) VALUES (?, ?, ?, ?, ?, NULL)",
            (str(run_id), now, "running", str(actor), 0),
        )

    assert lifecycle.delete_run(run_id, actor, actor) is LifecycleDeletionOutcome.ACTIVE

    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT deleted_at FROM analysis_runs WHERE run_id = ?",
            (str(run_id),),
        ).fetchone()[0] is None
        assert connection.execute(
            "SELECT outcome FROM management_audit WHERE action = 'analysis_run.delete'"
        ).fetchone()[0] == "rejected_active"

def test_snapshot_delete_is_rejected_while_parent_run_is_active(tmp_path):
    database = tmp_path / "analysis.db"
    SQLiteAnalysisRunStore(database)
    SQLiteManagementAuditStore(database)
    lifecycle = SQLiteAnalysisLifecycleStore(database)

    run_id = uuid4()
    snapshot_id = uuid4()
    actor = uuid4()
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO analysis_runs(run_id, created_at, state, owner_user_id, outcomes_available, deleted_at) VALUES (?, ?, ?, ?, ?, NULL)",
            (str(run_id), now, "running", str(actor), 0),
        )
        connection.execute(
            "INSERT INTO analysis_results(snapshot_id, symbol, analysis_date, payload, analysis_run_id, owner_user_id, deleted_at) VALUES (?, ?, ?, ?, ?, ?, NULL)",
            (str(snapshot_id), "EGAL", None, "{}", str(run_id), str(actor)),
        )

    assert lifecycle.delete_snapshot(snapshot_id, actor, actor) is LifecycleDeletionOutcome.ACTIVE

    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT deleted_at FROM analysis_results WHERE snapshot_id = ?",
            (str(snapshot_id),),
        ).fetchone()[0] is None
        assert connection.execute(
            "SELECT outcome FROM management_audit WHERE action = 'analysis_snapshot.delete'"
        ).fetchone()[0] == "rejected_active"
