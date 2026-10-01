from dataclasses import dataclass
from statistics import quantiles
from time import perf_counter
from typing import Callable


@dataclass(frozen=True)
class PerformanceSample:
    durations_seconds: tuple[float, ...]
    repetitions: int
    warmup_runs: int

    @property
    def p50_seconds(self) -> float:
        return _percentile(self.durations_seconds, 0.50)

    @property
    def p95_seconds(self) -> float:
        return _percentile(self.durations_seconds, 0.95)

    @property
    def p99_seconds(self) -> float:
        return _percentile(self.durations_seconds, 0.99)

    @property
    def operations_per_second(self) -> float:
        total = sum(self.durations_seconds)
        return self.repetitions / total if total else float("inf")


def measure(
    operation: Callable[[], object],
    *,
    repetitions: int = 5,
    warmup_runs: int = 2,
) -> PerformanceSample:
    if repetitions < 5:
        raise ValueError("repetitions must be at least 5")
    if warmup_runs < 0:
        raise ValueError("warmup_runs cannot be negative")

    for _ in range(warmup_runs):
        operation()

    durations: list[float] = []
    for _ in range(repetitions):
        started = perf_counter()
        operation()
        durations.append(perf_counter() - started)

    return PerformanceSample(
        durations_seconds=tuple(durations),
        repetitions=repetitions,
        warmup_runs=warmup_runs,
    )


def _percentile(values: tuple[float, ...], percentile: float) -> float:
    if not values:
        raise ValueError("at least one measurement is required")
    if len(values) == 1:
        return values[0]

    points = quantiles(values, n=100, method="inclusive")
    rank = max(1, min(100, round(percentile * 100)))
    return points[rank - 2] if rank == 1 else points[rank - 1]
