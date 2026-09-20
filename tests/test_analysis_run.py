from app.domain.analysis_run import AnalysisRun
from app.domain.execution import ExecutionState


def test_analysis_run_has_immutable_identity_and_creation_time():
    run = AnalysisRun.create()

    assert run.id is not None
    assert run.created_at.tzinfo is not None
    assert run.state is ExecutionState.CREATED


def test_analysis_run_can_transition_by_creating_a_new_record():
    run = AnalysisRun.create()

    completed = run.with_state(ExecutionState.COMPLETED)

    assert completed.id == run.id
    assert completed.created_at == run.created_at
    assert completed.state is ExecutionState.COMPLETED
    assert run.state is ExecutionState.CREATED
