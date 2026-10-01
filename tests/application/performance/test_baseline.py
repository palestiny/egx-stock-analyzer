import pytest

from app.application.performance.baseline import measure


def test_measure_warms_up_and_records_requested_repetitions() -> None:
    calls = 0

    def operation() -> None:
        nonlocal calls
        calls += 1

    sample = measure(operation, repetitions=5, warmup_runs=2)

    assert calls == 7
    assert sample.repetitions == 5
    assert sample.warmup_runs == 2
    assert len(sample.durations_seconds) == 5
    assert sample.p50_seconds > 0
    assert sample.p95_seconds >= sample.p50_seconds
    assert sample.p99_seconds >= sample.p95_seconds
    assert sample.operations_per_second > 0


def test_measure_requires_at_least_five_repetitions() -> None:
    with pytest.raises(ValueError, match="at least 5"):
        measure(lambda: None, repetitions=4)


def test_measure_rejects_negative_warmup() -> None:
    with pytest.raises(ValueError, match="warmup"):
        measure(lambda: None, warmup_runs=-1)


def test_measure_rejects_invalid_percentile_configuration() -> None:
    sample = measure(lambda: None, repetitions=5)

    assert sample.p50_seconds >= 0
