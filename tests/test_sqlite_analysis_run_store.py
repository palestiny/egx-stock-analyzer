import sqlite3
from datetime import datetime, timezone
from uuid import UUID

from app.domain.analysis_run import AnalysisRun
from app.domain.execution import ExecutionState
from app.infrastructure.persistence.sqlite_analysis_run_store import (
    SQLiteAnalysisRunStore,
)


def test_analysis_run_store_round_trip_and_restart(tmp_path):
    database = tmp_path / "analysis.db"
    run = AnalysisRun.create().with_state(ExecutionState.RUNNING)

    SQLiteAnalysisRunStore(database).save(run)

    restored = SQLiteAnalysisRunStore(database).get(run.id)

    assert restored == run


def test_analysis_run_store_updates_terminal_state(tmp_path):
    database = tmp_path / "analysis.db"
    store = SQLiteAnalysisRunStore(database)
    run = AnalysisRun.create()

    store.save(run)
    completed = run.with_state(ExecutionState.COMPLETED)
    store.save(completed)

    assert store.get(run.id) == completed


def test_analysis_run_store_creates_durable_table(tmp_path):
    database = tmp_path / "analysis.db"

    SQLiteAnalysisRunStore(database)

    with sqlite3.connect(database) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(analysis_runs)"
            ).fetchall()
        }

    assert columns == {"run_id", "created_at", "state", "owner_user_id", "outcomes_available"}


def test_sqlite_list_runs_is_deterministic_and_restart_safe(tmp_path):
    database = tmp_path / "analysis.db"
    store = SQLiteAnalysisRunStore(database)
    older = AnalysisRun(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        created_at=datetime(2026, 9, 20, 8, tzinfo=timezone.utc),
        state=ExecutionState.COMPLETED,
    )
    newer = AnalysisRun(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        created_at=datetime(2026, 9, 20, 9, tzinfo=timezone.utc),
        state=ExecutionState.FAILED,
    )
    store.save(older)
    store.save(newer)

    restored = SQLiteAnalysisRunStore(database).list_runs(limit=10)
    filtered = SQLiteAnalysisRunStore(database).list_runs(
        state=ExecutionState.FAILED,
        limit=10,
    )

    assert [run.id for run in restored] == [newer.id, older.id]
    assert [run.id for run in filtered] == [newer.id]


def test_sqlite_analysis_run_owner_survives_restart(tmp_path):
    from uuid import uuid4
    from app.domain.analysis_run import AnalysisRun
    from app.infrastructure.persistence.sqlite_analysis_run_store import SQLiteAnalysisRunStore

    database_path = tmp_path / "analysis.db"
    owner_id = uuid4()
    run = AnalysisRun.create(owner_user_id=owner_id)

    SQLiteAnalysisRunStore(database_path).save(run)
    restored = SQLiteAnalysisRunStore(database_path).get(run.id)

    assert restored is not None
    assert restored.owner_user_id == owner_id


def test_sqlite_analysis_run_owner_filter_excludes_other_users(tmp_path):
    from uuid import uuid4
    from app.domain.analysis_run import AnalysisRun
    from app.infrastructure.persistence.sqlite_analysis_run_store import SQLiteAnalysisRunStore

    database_path = tmp_path / "analysis.db"
    owner_id = uuid4()
    other_id = uuid4()
    store = SQLiteAnalysisRunStore(database_path)
    store.save(AnalysisRun.create(owner_user_id=owner_id))
    store.save(AnalysisRun.create(owner_user_id=other_id))
    store.save(AnalysisRun.create())

    runs = store.list_runs(owner_user_id=owner_id)

    assert len(runs) == 1
    assert runs[0].owner_user_id == owner_id


def test_sqlite_analysis_run_legacy_schema_migrates_owner_as_global(tmp_path):
    import sqlite3
    from app.infrastructure.persistence.sqlite_analysis_run_store import SQLiteAnalysisRunStore

    database_path = tmp_path / "legacy.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE analysis_runs (run_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, state TEXT NOT NULL, outcomes_available INTEGER NOT NULL DEFAULT 0)"
        )

    store = SQLiteAnalysisRunStore(database_path)
    assert store.list_runs() == ()
