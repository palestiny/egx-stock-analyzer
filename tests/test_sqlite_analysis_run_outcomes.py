from app.domain.analysis_run import AnalysisRun, AnalysisRunOutcome
from app.domain.execution import ExecutionState


def test_sqlite_analysis_run_store_persists_outcomes(tmp_path):
    from uuid import uuid4

    from app.infrastructure.persistence.sqlite_analysis_run_store import SQLiteAnalysisRunStore

    database_path = tmp_path / "analysis.db"
    stock_id = uuid4()
    run = (
        AnalysisRun.create()
        .with_state(ExecutionState.COMPLETED_WITH_ERRORS)
        .with_outcomes(
            (
                AnalysisRunOutcome.success("EGAL", stock_id),
                AnalysisRunOutcome.failed("UNKNOWN", "UNKNOWN_SYMBOL", "UNKNOWN"),
            )
        )
    )

    SQLiteAnalysisRunStore(database_path).save(run)
    restored = SQLiteAnalysisRunStore(database_path).get(run.id)

    assert restored == run


def test_sqlite_analysis_run_store_legacy_run_has_empty_outcomes(tmp_path):
    from app.infrastructure.persistence.sqlite_analysis_run_store import SQLiteAnalysisRunStore

    database_path = tmp_path / "analysis.db"
    store = SQLiteAnalysisRunStore(database_path)
    run = AnalysisRun.create()
    store.save(run)

    restored = SQLiteAnalysisRunStore(database_path).get(run.id)

    assert restored is not None
    assert restored.outcomes == ()
