import sqlite3

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

    assert columns == {"run_id", "created_at", "state"}


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
