from app.application.execution.orchestrator import ExecutionOrchestrator
from app.application.execution.retry import RetryPolicy
from app.domain.execution import ExecutionState


def test_orchestrator_runs_all_stocks_and_finishes_successfully():
    execution = ExecutionOrchestrator(RetryPolicy(max_attempts=1)).run(
        ["EGAL", "IEEC"],
        lambda stock_id: None,
    )

    assert execution.state == ExecutionState.COMPLETED
    assert execution.successful_stock_ids == {"EGAL", "IEEC"}
    assert execution.failed_stock_ids == set()


def test_orchestrator_continues_after_one_stock_fails():
    def analyze(stock_id: str) -> None:
        if stock_id == "IEEC":
            raise ValueError("analysis failed")

    execution = ExecutionOrchestrator(RetryPolicy(max_attempts=1)).run(
        ["EGAL", "IEEC"],
        analyze,
    )

    assert execution.state == ExecutionState.COMPLETED_WITH_ERRORS
    assert execution.successful_stock_ids == {"EGAL"}
    assert execution.failed_stock_ids == {"IEEC"}
    assert execution.failure_reasons == {"IEEC": "analysis failed"}


def test_orchestrator_can_propagate_selected_exceptions():
    def fail(_: str) -> None:
        raise RuntimeError("must propagate")

    try:
        ExecutionOrchestrator(
            RetryPolicy(max_attempts=3),
            propagate_exceptions=(RuntimeError,),
        ).run(["EGAL"], fail)
    except RuntimeError as error:
        assert str(error) == "must propagate"
    else:
        raise AssertionError("Expected RuntimeError to propagate")
