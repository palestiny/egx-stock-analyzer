import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from app.application.analysis.automatic_analysis_retention import (
    AutomaticAnalysisRetention,
    AutomaticRetentionPolicy,
)
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


def _insert_deleted_run(database, deleted_at, run_id=None):
    run_id = run_id or uuid4()
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO analysis_runs(
                run_id, created_at, state, owner_user_id, outcomes_available, deleted_at
            )
            VALUES (?, ?, 'completed', NULL, 1, ?)
            """,
            (str(run_id), deleted_at, deleted_at),
        )
    return run_id


def _insert_runless_snapshot(database, deleted_at, snapshot_id=None):
    snapshot_id = snapshot_id or uuid4()
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


def test_policy_defaults_to_disabled_and_thirty_days():
    policy = AutomaticRetentionPolicy()
    assert policy.enabled is False
    assert policy.preservation_days == 30
    assert policy.batch_limit == 100


@pytest.mark.parametrize("days", [0, -1])
def test_policy_rejects_non_positive_preservation_days(days):
    with pytest.raises(ValueError):
        AutomaticRetentionPolicy(enabled=True, preservation_days=days)


def test_disabled_policy_does_not_delete(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    deleted_at = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    run_id = _insert_deleted_run(database, deleted_at)

    actor = AuthenticatedIdentity.operator()
    result = AutomaticAnalysisRetention(
        lifecycle, AutomaticRetentionPolicy(enabled=False)
    ).execute(
        actor,
        now=datetime.now(timezone.utc),
    )

    assert result.purged_run_ids == ()
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT 1 FROM analysis_runs WHERE run_id = ?", (str(run_id),)
        ).fetchone() is not None


def test_eligible_boundary_is_exactly_thirty_days(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    now = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
    eligible = _insert_deleted_run(
        database, (now - timedelta(days=30)).isoformat()
    )
    too_new = _insert_deleted_run(
        database, (now - timedelta(days=29, seconds=1)).isoformat()
    )

    result = AutomaticAnalysisRetention(
        lifecycle, AutomaticRetentionPolicy(enabled=True)
    ).execute(
        AuthenticatedIdentity.operator(),
        now=now,
    )

    assert result.purged_run_ids == (eligible,)
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT 1 FROM analysis_runs WHERE run_id = ?", (str(too_new),)
        ).fetchone() is not None


def test_runless_snapshot_is_eligible_after_thirty_days(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    now = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
    snapshot_id = _insert_runless_snapshot(
        database, (now - timedelta(days=31)).isoformat()
    )

    result = AutomaticAnalysisRetention(lifecycle).execute(
        AuthenticatedIdentity.operator(),
        policy=AutomaticRetentionPolicy(enabled=True),
        now=now,
    )

    assert result.purged_snapshot_ids == (snapshot_id,)


def test_batch_limit_is_enforced(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    now = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
    ids = sorted(
        (_insert_deleted_run(database, (now - timedelta(days=31)).isoformat()) for _ in range(3)),
        key=str,
    )

    result = AutomaticAnalysisRetention(
        lifecycle, AutomaticRetentionPolicy(enabled=True, batch_limit=2)
    ).execute(
        AuthenticatedIdentity.operator(),
        now=now,
    )

    assert result.purged_run_ids == tuple(ids[:2])


def test_automatic_retention_uses_distinct_audit_operation(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    now = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
    run_id = _insert_deleted_run(
        database, (now - timedelta(days=31)).isoformat()
    )

    actor = AuthenticatedIdentity.operator()
    result = AutomaticAnalysisRetention(
        lifecycle, AutomaticRetentionPolicy(enabled=True)
    ).execute(
        actor,
        now=now,
    )

    assert result.purged_run_ids == (run_id,)
    with sqlite3.connect(database) as connection:
        action = connection.execute(
            "SELECT action FROM management_audit WHERE target_user_id = ? ORDER BY id DESC LIMIT 1",
            (str(actor.user_id),),
        ).fetchone()[0]
    assert action.startswith("analysis_lifecycle.automatic_retention:")


def test_invalid_configuration_fails_before_deletion(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    deleted_at = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    run_id = _insert_deleted_run(database, deleted_at)

    with pytest.raises(ValueError):
        AutomaticAnalysisRetention(
            lifecycle, AutomaticRetentionPolicy(enabled=True, preservation_days=0)
        ).execute(
            AuthenticatedIdentity.operator(),
            now=datetime.now(timezone.utc),
        )

    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT 1 FROM analysis_runs WHERE run_id = ?", (str(run_id),)
        ).fetchone() is not None


def test_dry_run_is_non_destructive_and_uses_automatic_audit_identity(tmp_path):
    database = tmp_path / "analysis.db"
    lifecycle = _stores(database)
    actor = AuthenticatedIdentity.operator()
    now = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
    run_id = _insert_deleted_run(
        database, (now - timedelta(days=31)).isoformat()
    )

    result = AutomaticAnalysisRetention(
        lifecycle, AutomaticRetentionPolicy(enabled=True)
    ).execute(
        actor,
        now=now,
        dry_run=True,
    )

    assert result.purge is not None
    assert result.purge.dry_run is True
    assert result.purged_run_ids == ()
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT 1 FROM analysis_runs WHERE run_id = ?", (str(run_id),)
        ).fetchone() is not None
        action = connection.execute(
            "SELECT action FROM management_audit ORDER BY id DESC LIMIT 1"
        ).fetchone()[0]
    assert action.startswith("analysis_lifecycle.automatic_retention:")
