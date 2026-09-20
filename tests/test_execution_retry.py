from app.application.execution.retry import RetryPolicy, RetryableError


def test_transient_failure_is_retryable():
    policy = RetryPolicy(max_attempts=3)

    assert policy.should_retry(RetryableError("temporary"), attempt=1)


def test_retry_stops_at_max_attempts():
    policy = RetryPolicy(max_attempts=3)

    assert not policy.should_retry(RetryableError("temporary"), attempt=3)


def test_permanent_failure_is_not_retryable():
    policy = RetryPolicy(max_attempts=3)

    assert not policy.should_retry(ValueError("invalid"), attempt=1)
