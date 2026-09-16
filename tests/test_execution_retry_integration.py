from app.application.execution.retry import RetryPolicy, RetryableError
from app.application.execution.runner import ExecutionRunner
from app.domain.execution import Execution, ExecutionState


def test_transient_failure_retries_then_records_success():
    execution = Execution.create()
    execution.start()
    policy = RetryPolicy(max_attempts=3)
    runner = ExecutionRunner(policy)
    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RetryableError("temporary")

    runner.run_stock(execution, "EGAL", operation)

    assert attempts == 3
    assert execution.state == ExecutionState.RUNNING
    assert "EGAL" in execution.successful_stock_ids
    assert "EGAL" not in execution.failed_stock_ids


def test_retry_exhaustion_records_stock_failure_and_continues():
    execution = Execution.create()
    execution.start()
    policy = RetryPolicy(max_attempts=2)
    runner = ExecutionRunner(policy)

    def operation():
        raise RetryableError("temporary")

    runner.run_stock(execution, "IEEC", operation)

    assert execution.state == ExecutionState.RUNNING
    assert "IEEC" in execution.failed_stock_ids


def test_permanent_failure_records_stock_failure_without_retry():
    execution = Execution.create()
    execution.start()
    policy = RetryPolicy(max_attempts=3)
    runner = ExecutionRunner(policy)
    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1
        raise ValueError("invalid")

    runner.run_stock(execution, "SVCE", operation)

    assert attempts == 1
    assert "SVCE" in execution.failed_stock_ids
