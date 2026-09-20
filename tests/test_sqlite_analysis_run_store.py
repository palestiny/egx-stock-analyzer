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


def test_analysis_run_and_snapshot_correlation_survives_restart(tmp_path):
    from datetime import date
    from uuid import uuid4

    from app.infrastructure.persistence.sqlite_analysis_result_store import (
        SQLiteAnalysisResultStore,
    )
    from tests.test_sqlite_analysis_result_store import make_result

    database = tmp_path / "analysis.db"
    run = AnalysisRun.create().with_state(ExecutionState.COMPLETED)
    result_store = SQLiteAnalysisResultStore(database)
    run_store = SQLiteAnalysisRunStore(database)

    run_store.save(run)
    result_store.save(
        "EGAL",
        make_result(),
        date(2026, 9, 20),
        analysis_run_id=run.id,
    )

    restored_run_store = SQLiteAnalysisRunStore(database)
    restored_result_store = SQLiteAnalysisResultStore(database)
    restored_run = restored_run_store.get(run.id)
    snapshot = restored_result_store.get_history("EGAL")[0]

    assert restored_run == run
    assert snapshot.analysis_run_id == run.id
    assert uuid4() != run.id
