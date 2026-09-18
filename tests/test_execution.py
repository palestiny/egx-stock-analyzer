from app.domain.execution import Execution, ExecutionState


def test_new_execution_starts_created():
    execution = Execution.create()

    assert execution.state == ExecutionState.CREATED


def test_execution_can_start():
    execution = Execution.create()

    execution.start()

    assert execution.state == ExecutionState.RUNNING


def test_running_execution_can_complete():
    execution = Execution.create()
    execution.start()

    execution.complete()

    assert execution.state == ExecutionState.COMPLETED


def test_running_execution_can_complete_with_errors():
    execution = Execution.create()
    execution.start()

    execution.complete_with_errors()

    assert execution.state == ExecutionState.COMPLETED_WITH_ERRORS


def test_running_execution_can_fail():
    execution = Execution.create()
    execution.start()

    execution.fail()

    assert execution.state == ExecutionState.FAILED


def test_running_execution_can_be_cancelled():
    execution = Execution.create()
    execution.start()

    execution.cancel()

    assert execution.state == ExecutionState.CANCELLED


def test_execution_cannot_complete_before_running():
    execution = Execution.create()

    try:
        execution.complete()
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_execution_cannot_start_twice():
    execution = Execution.create()
    execution.start()

    try:
        execution.start()
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_execution_records_successful_stock():
    execution = Execution.create()
    execution.start()

    execution.record_stock_success("EGAL")

    assert execution.successful_stock_ids == {"EGAL"}


def test_execution_records_failed_stock():
    execution = Execution.create()
    execution.start()

    execution.record_stock_failure("IEEC")

    assert execution.failed_stock_ids == {"IEEC"}


def test_execution_completes_when_all_stocks_succeed():
    execution = Execution.create()
    execution.start()
    execution.record_stock_success("EGAL")
    execution.record_stock_success("IEEC")

    execution.finish()

    assert execution.state == ExecutionState.COMPLETED


def test_execution_completes_with_errors_when_some_stocks_fail():
    execution = Execution.create()
    execution.start()
    execution.record_stock_success("EGAL")
    execution.record_stock_failure("IEEC")

    execution.finish()

    assert execution.state == ExecutionState.COMPLETED_WITH_ERRORS


def test_execution_fails_when_all_stocks_fail():
    execution = Execution.create()
    execution.start()
    execution.record_stock_failure("EGAL")
    execution.record_stock_failure("IEEC")

    execution.finish()

    assert execution.state == ExecutionState.FAILED


def test_execution_records_failure_reason():
    execution = Execution.create()
    execution.start()

    execution.record_stock_failure("IEEC", reason="analysis failed")

    assert execution.failure_reasons == {"IEEC": "analysis failed"}


def test_execution_success_clears_previous_failure_reason():
    execution = Execution.create()
    execution.start()

    execution.record_stock_failure("IEEC", reason="analysis failed")
    execution.record_stock_success("IEEC")

    assert execution.failure_reasons == {}
