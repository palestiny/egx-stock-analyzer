from collections.abc import Sequence
from decimal import Decimal

IndicatorSeries = tuple[Decimal | None, ...]


def _validated_values(values: Sequence[Decimal], period: int) -> tuple[Decimal, ...]:
    if period < 1:
        raise ValueError("period must be a positive integer")
    normalized = tuple(values)
    if any(not value.is_finite() for value in normalized):
        raise ValueError("indicator inputs must be finite Decimal values")
    return normalized


def simple_moving_average(values: Sequence[Decimal], period: int) -> IndicatorSeries:
    """Return an index-aligned SMA series; values before the first full window are None."""
    samples = _validated_values(values, period)
    result: list[Decimal | None] = [None] * len(samples)
    rolling_sum = Decimal("0")

    for index, value in enumerate(samples):
        rolling_sum += value
        if index >= period:
            rolling_sum -= samples[index - period]
        if index >= period - 1:
            result[index] = rolling_sum / Decimal(period)

    return tuple(result)


def exponential_moving_average(values: Sequence[Decimal], period: int) -> IndicatorSeries:
    """Return an index-aligned EMA seeded by the first complete SMA window."""
    samples = _validated_values(values, period)
    result: list[Decimal | None] = [None] * len(samples)
    if len(samples) < period:
        return tuple(result)

    seed_index = period - 1
    seed = sum(samples[:period], Decimal("0")) / Decimal(period)
    result[seed_index] = seed
    multiplier = Decimal("2") / Decimal(period + 1)
    previous = seed

    for index in range(period, len(samples)):
        current = (samples[index] - previous) * multiplier + previous
        result[index] = current
        previous = current

    return tuple(result)
