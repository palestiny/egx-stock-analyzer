from collections.abc import Sequence
from dataclasses import dataclass
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
    """Return an index-aligned EMA series seeded by the first complete SMA window."""
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


def relative_strength_index(values: Sequence[Decimal], period: int = 14) -> IndicatorSeries:
    """Calculate Wilder RSI; output remains index-aligned with the input series."""
    samples = _validated_values(values, period)
    result: list[Decimal | None] = [None] * len(samples)
    if len(samples) <= period:
        return tuple(result)

    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for previous, current in zip(samples, samples[1:]):
        change = current - previous
        gains.append(max(change, Decimal("0")))
        losses.append(max(-change, Decimal("0")))

    average_gain = sum(gains[:period], Decimal("0")) / Decimal(period)
    average_loss = sum(losses[:period], Decimal("0")) / Decimal(period)

    def rsi(gain: Decimal, loss: Decimal) -> Decimal:
        if gain == 0 and loss == 0:
            return Decimal("50")
        if loss == 0:
            return Decimal("100")
        relative_strength = gain / loss
        return Decimal("100") - (Decimal("100") / (Decimal("1") + relative_strength))

    result[period] = rsi(average_gain, average_loss)
    for change_index in range(period, len(gains)):
        average_gain = (
            average_gain * Decimal(period - 1) + gains[change_index]
        ) / Decimal(period)
        average_loss = (
            average_loss * Decimal(period - 1) + losses[change_index]
        ) / Decimal(period)
        result[change_index + 1] = rsi(average_gain, average_loss)

    return tuple(result)


@dataclass(frozen=True)
class MACDSeries:
    line: IndicatorSeries
    signal: IndicatorSeries
    histogram: IndicatorSeries


def macd(
    values: Sequence[Decimal],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> MACDSeries:
    """Calculate MACD with SMA-seeded EMAs and aligned warm-up gaps."""
    samples = tuple(values)
    if fast_period < 1 or slow_period < 1 or signal_period < 1:
        raise ValueError("period must be a positive integer")
    if fast_period >= slow_period:
        raise ValueError("fast_period must be less than slow_period")
    if any(not value.is_finite() for value in samples):
        raise ValueError("indicator inputs must be finite Decimal values")

    fast = exponential_moving_average(samples, fast_period)
    slow = exponential_moving_average(samples, slow_period)
    line: list[Decimal | None] = [
        (fast_value - slow_value)
        if fast_value is not None and slow_value is not None
        else None
        for fast_value, slow_value in zip(fast, slow)
    ]
    first_valid = next((i for i, value in enumerate(line) if value is not None), None)
    signal: list[Decimal | None] = [None] * len(samples)
    histogram: list[Decimal | None] = [None] * len(samples)

    if first_valid is None:
        return MACDSeries(tuple(line), tuple(signal), tuple(histogram))

    valid_line = [value for value in line[first_valid:] if value is not None]
    valid_signal = exponential_moving_average(valid_line, signal_period)
    for offset, signal_value in enumerate(valid_signal):
        index = first_valid + offset
        signal[index] = signal_value
        if signal_value is not None and line[index] is not None:
            histogram[index] = line[index] - signal_value

    return MACDSeries(tuple(line), tuple(signal), tuple(histogram))
