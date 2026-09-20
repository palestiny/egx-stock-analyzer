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
