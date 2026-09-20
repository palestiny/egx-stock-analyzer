from app.application.analysis.get_analysis_run import GetAnalysisRun
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.analysis.run_store import InMemoryAnalysisRunStore
from app.domain.analysis_run import AnalysisRun, AnalysisRunOutcome
from app.domain.execution import ExecutionState


def test_run_detail_returns_durable_outcomes_in_symbol_order():
    run_store = InMemoryAnalysisRunStore()
    result_store = InMemoryAnalysisResultStore()
    run = (
        AnalysisRun.create()
        .with_state(ExecutionState.COMPLETED_WITH_ERRORS)
        .with_outcomes(
            (
                AnalysisRunOutcome.failed("SVCE", "ANALYSIS_FAILED"),
                AnalysisRunOutcome.success("EGAL"),
            )
        )
    )
    run_store.save(run)

    view = GetAnalysisRun(run_store, result_store).execute(run.id)

    assert view.outcomes_available is True
    assert [item.symbol for item in view.outcomes] == ["EGAL", "SVCE"]
    assert view.outcomes[0].state == "success"
    assert view.outcomes[1].failure_code == "ANALYSIS_FAILED"


def test_legacy_run_detail_marks_outcomes_unavailable():
    run_store = InMemoryAnalysisRunStore()
    result_store = InMemoryAnalysisResultStore()
    run = AnalysisRun.create().with_state(ExecutionState.FAILED)
    run_store.save(run)

    view = GetAnalysisRun(run_store, result_store).execute(run.id)

    assert view.outcomes_available is False
    assert view.outcomes == ()
