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
        line_value = line[index]
        if signal_value is not None and line_value is not None:
            histogram[index] = line_value - signal_value

    return MACDSeries(tuple(line), tuple(signal), tuple(histogram))


@dataclass(frozen=True)
class BollingerBands:
    upper: IndicatorSeries
    middle: IndicatorSeries
    lower: IndicatorSeries


def bollinger_bands(
    values: Sequence[Decimal],
    period: int = 20,
    standard_deviations: Decimal = Decimal("2"),
) -> BollingerBands:
    """Calculate population-standard-deviation Bollinger bands with aligned warm-up gaps."""
    samples = _validated_values(values, period)
    if not standard_deviations.is_finite() or standard_deviations < 0:
        raise ValueError("standard_deviations must be finite and non-negative")
    middle = simple_moving_average(samples, period)
    upper: list[Decimal | None] = [None] * len(samples)
    lower: list[Decimal | None] = [None] * len(samples)

    for index in range(period - 1, len(samples)):
        window = samples[index - period + 1:index + 1]
        mean = sum(window, Decimal("0")) / Decimal(period)
        variance = sum(((value - mean) ** 2 for value in window), Decimal("0")) / Decimal(period)
        deviation = variance.sqrt()
        upper[index] = mean + standard_deviations * deviation
        lower[index] = mean - standard_deviations * deviation

    return BollingerBands(tuple(upper), middle, tuple(lower))


def average_true_range(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    closes: Sequence[Decimal],
    period: int = 14,
) -> IndicatorSeries:
    """Calculate Wilder ATR from aligned high, low, and close observations."""
    if period < 1:
        raise ValueError("period must be a positive integer")
    high_values = tuple(highs)
    low_values = tuple(lows)
    close_values = tuple(closes)
    if not (len(high_values) == len(low_values) == len(close_values)):
        raise ValueError("highs, lows, and closes must have equal lengths")
    if any(
        not value.is_finite()
        for value in (*high_values, *low_values, *close_values)
    ):
        raise ValueError("indicator inputs must be finite Decimal values")
    for high, low in zip(high_values, low_values):
        if high < low:
            raise ValueError("each high must be greater than or equal to its low")

    result: list[Decimal | None] = [None] * len(high_values)
    true_ranges: list[Decimal] = []
    for index, (high, low, close) in enumerate(zip(high_values, low_values, close_values)):
        if index == 0:
            true_range = high - low
        else:
            true_range = max(
                high - low,
                abs(high - close_values[index - 1]),
                abs(low - close_values[index - 1]),
            )
        true_ranges.append(true_range)

    if len(true_ranges) < period:
        return tuple(result)

    previous_atr = sum(true_ranges[:period], Decimal("0")) / Decimal(period)
    result[period - 1] = previous_atr
    for index in range(period, len(true_ranges)):
        previous_atr = (
            previous_atr * Decimal(period - 1) + true_ranges[index]
        ) / Decimal(period)
        result[index] = previous_atr

    return tuple(result)


@dataclass(frozen=True)
class StochasticSeries:
    percent_k: IndicatorSeries
    percent_d: IndicatorSeries


def stochastic_oscillator(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    closes: Sequence[Decimal],
    k_period: int = 14,
    d_period: int = 3,
) -> StochasticSeries:
    """Calculate slow %K/%D; flat windows are marked unavailable, not neutral."""
    if k_period < 1 or d_period < 1:
        raise ValueError("period must be a positive integer")
    high_values, low_values, close_values = tuple(highs), tuple(lows), tuple(closes)
    if not (len(high_values) == len(low_values) == len(close_values)):
        raise ValueError("highs, lows, and closes must have equal lengths")
    if any(
        not value.is_finite()
        for value in (*high_values, *low_values, *close_values)
    ):
        raise ValueError("indicator inputs must be finite Decimal values")

    percent_k: list[Decimal | None] = [None] * len(close_values)
    for index in range(k_period - 1, len(close_values)):
        start = index - k_period + 1
        highest = max(high_values[start:index + 1])
        lowest = min(low_values[start:index + 1])
        if highest > lowest:
            percent_k[index] = (
                (close_values[index] - lowest) / (highest - lowest)
            ) * Decimal("100")

    percent_d: list[Decimal | None] = [None] * len(close_values)
    for index in range(len(close_values)):
        start = index - d_period + 1
        if start < 0:
            continue
        window = percent_k[start:index + 1]
        if all(value is not None for value in window):
            percent_d[index] = sum(
                (value for value in window if value is not None), Decimal("0")
            ) / Decimal(d_period)

    return StochasticSeries(tuple(percent_k), tuple(percent_d))


def commodity_channel_index(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    closes: Sequence[Decimal],
    period: int = 20,
) -> IndicatorSeries:
    """Calculate CCI from typical price and mean absolute deviation."""
    if period < 1:
        raise ValueError("period must be a positive integer")
    high_values, low_values, close_values = tuple(highs), tuple(lows), tuple(closes)
    if not (len(high_values) == len(low_values) == len(close_values)):
        raise ValueError("highs, lows, and closes must have equal lengths")
    if any(
        not value.is_finite()
        for value in (*high_values, *low_values, *close_values)
    ):
        raise ValueError("indicator inputs must be finite Decimal values")

    typical = tuple(
        (high + low + close) / Decimal("3")
        for high, low, close in zip(high_values, low_values, close_values)
    )
    result: list[Decimal | None] = [None] * len(typical)
    for index in range(period - 1, len(typical)):
        window = typical[index - period + 1:index + 1]
        mean = sum(window, Decimal("0")) / Decimal(period)
        mean_deviation = sum(
            (abs(value - mean) for value in window), Decimal("0")
        ) / Decimal(period)
        if mean_deviation != 0:
            result[index] = (typical[index] - mean) / (Decimal("0.015") * mean_deviation)

    return tuple(result)


def on_balance_volume(
    closes: Sequence[Decimal],
    volumes: Sequence[int],
) -> tuple[int | None, ...]:
    """Calculate cumulative OBV; the first observation establishes a zero baseline."""
    close_values, volume_values = tuple(closes), tuple(volumes)
    if len(close_values) != len(volume_values):
        raise ValueError("closes and volumes must have equal lengths")
    if any(not value.is_finite() for value in close_values):
        raise ValueError("indicator inputs must be finite Decimal values")
    if any(isinstance(volume, bool) or not isinstance(volume, int) or volume < 0 for volume in volume_values):
        raise ValueError("volumes must be non-negative integers")
    if not close_values:
        return ()

    result: list[int | None] = [0]
    current = 0
    for index in range(1, len(close_values)):
        if close_values[index] > close_values[index - 1]:
            current += volume_values[index]
        elif close_values[index] < close_values[index - 1]:
            current -= volume_values[index]
        result.append(current)
    return tuple(result)


def money_flow_index(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    closes: Sequence[Decimal],
    volumes: Sequence[int],
    period: int = 14,
) -> IndicatorSeries:
    """Calculate MFI from typical-price money flow and direction changes."""
    if period < 1:
        raise ValueError("period must be a positive integer")
    high_values, low_values, close_values, volume_values = (
        tuple(highs), tuple(lows), tuple(closes), tuple(volumes)
    )
    if not (len(high_values) == len(low_values) == len(close_values) == len(volume_values)):
        raise ValueError("OHLC and volume inputs must have equal lengths")
    if any(
        not value.is_finite()
        for value in (*high_values, *low_values, *close_values)
    ):
        raise ValueError("indicator inputs must be finite Decimal values")
    if any(isinstance(volume, bool) or not isinstance(volume, int) or volume < 0 for volume in volume_values):
        raise ValueError("volumes must be non-negative integers")

    typical = tuple(
        (high + low + close) / Decimal("3")
        for high, low, close in zip(high_values, low_values, close_values)
    )
    raw_flow = tuple(
        price * Decimal(volume)
        for price, volume in zip(typical, volume_values)
    )
    result: list[Decimal | None] = [None] * len(typical)

    for index in range(period, len(typical)):
        positive = Decimal("0")
        negative = Decimal("0")
        for flow_index in range(index - period + 1, index + 1):
            if typical[flow_index] > typical[flow_index - 1]:
                positive += raw_flow[flow_index]
            elif typical[flow_index] < typical[flow_index - 1]:
                negative += raw_flow[flow_index]
        if positive == 0 and negative == 0:
            result[index] = Decimal("50")
        elif negative == 0:
            result[index] = Decimal("100")
        elif positive == 0:
            result[index] = Decimal("0")
        else:
            ratio = positive / negative
            result[index] = Decimal("100") - Decimal("100") / (Decimal("1") + ratio)

    return tuple(result)


@dataclass(frozen=True)
class DirectionalMovementSeries:
    plus_di: IndicatorSeries
    minus_di: IndicatorSeries
    adx: IndicatorSeries


def average_directional_index(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    closes: Sequence[Decimal],
    period: int = 14,
) -> DirectionalMovementSeries:
    """Calculate Wilder +DI, -DI, and ADX with explicit warm-up gaps."""
    if period < 1:
        raise ValueError("period must be a positive integer")
    high_values, low_values, close_values = tuple(highs), tuple(lows), tuple(closes)
    if not (len(high_values) == len(low_values) == len(close_values)):
        raise ValueError("highs, lows, and closes must have equal lengths")
    if any(
        not value.is_finite()
        for value in (*high_values, *low_values, *close_values)
    ):
        raise ValueError("indicator inputs must be finite Decimal values")
    if any(high < low for high, low in zip(high_values, low_values)):
        raise ValueError("each high must be greater than or equal to its low")

    count = len(high_values)
    plus_di: list[Decimal | None] = [None] * count
    minus_di: list[Decimal | None] = [None] * count
    adx: list[Decimal | None] = [None] * count
    if count < period:
        return DirectionalMovementSeries(tuple(plus_di), tuple(minus_di), tuple(adx))

    true_ranges: list[Decimal] = []
    plus_moves: list[Decimal] = []
    minus_moves: list[Decimal] = []
    for index in range(count):
        if index == 0:
            true_ranges.append(high_values[index] - low_values[index])
            plus_moves.append(Decimal("0"))
            minus_moves.append(Decimal("0"))
            continue
        up_move = high_values[index] - high_values[index - 1]
        down_move = low_values[index - 1] - low_values[index]
        plus_moves.append(up_move if up_move > down_move and up_move > 0 else Decimal("0"))
        minus_moves.append(down_move if down_move > up_move and down_move > 0 else Decimal("0"))
        true_ranges.append(max(
            high_values[index] - low_values[index],
            abs(high_values[index] - close_values[index - 1]),
            abs(low_values[index] - close_values[index - 1]),
        ))

    smoothed_tr = sum(true_ranges[:period], Decimal("0"))
    smoothed_plus = sum(plus_moves[:period], Decimal("0"))
    smoothed_minus = sum(minus_moves[:period], Decimal("0"))
    dx_values: list[Decimal | None] = [None] * count

    for index in range(period - 1, count):
        if index >= period:
            smoothed_tr = smoothed_tr - smoothed_tr / Decimal(period) + true_ranges[index]
            smoothed_plus = smoothed_plus - smoothed_plus / Decimal(period) + plus_moves[index]
            smoothed_minus = smoothed_minus - smoothed_minus / Decimal(period) + minus_moves[index]
        if smoothed_tr == 0:
            plus_di[index] = Decimal("0")
            minus_di[index] = Decimal("0")
            dx_values[index] = Decimal("0")
            continue
        plus_value = Decimal("100") * smoothed_plus / smoothed_tr
        minus_value = Decimal("100") * smoothed_minus / smoothed_tr
        plus_di[index] = plus_value
        minus_di[index] = minus_value
        denominator = plus_value + minus_value
        dx_values[index] = (
            Decimal("0")
            if denominator == 0
            else Decimal("100") * abs(plus_value - minus_value) / denominator
        )

    first_adx_index = 2 * period - 2
    if count > first_adx_index:
        first_dx_window = [
            value for value in dx_values[period - 1:first_adx_index + 1]
            if value is not None
        ]
        if len(first_dx_window) == period:
            previous_adx = sum(first_dx_window, Decimal("0")) / Decimal(period)
            adx[first_adx_index] = previous_adx
            for index in range(first_adx_index + 1, count):
                current_dx = dx_values[index]
                if current_dx is None:
                    continue
                previous_adx = (
                    previous_adx * Decimal(period - 1) + current_dx
                ) / Decimal(period)
                adx[index] = previous_adx

    return DirectionalMovementSeries(tuple(plus_di), tuple(minus_di), tuple(adx))


@dataclass(frozen=True)
class IchimokuSeries:
    conversion_line: IndicatorSeries
    base_line: IndicatorSeries
    leading_span_a_unshifted: IndicatorSeries
    leading_span_b_unshifted: IndicatorSeries


def ichimoku_cloud(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    *,
    conversion_period: int = 9,
    base_period: int = 26,
    span_b_period: int = 52,
) -> IchimokuSeries:
    """Calculate unshifted Ichimoku components; chart displacement is a presentation concern."""
    periods = (conversion_period, base_period, span_b_period)
    if any(period < 1 for period in periods):
        raise ValueError("period must be a positive integer")
    high_values, low_values = tuple(highs), tuple(lows)
    if len(high_values) != len(low_values):
        raise ValueError("highs and lows must have equal lengths")
    if any(not value.is_finite() for value in (*high_values, *low_values)):
        raise ValueError("indicator inputs must be finite Decimal values")
    if any(high < low for high, low in zip(high_values, low_values)):
        raise ValueError("each high must be greater than or equal to its low")

    def midpoint(period: int) -> IndicatorSeries:
        values: list[Decimal | None] = [None] * len(high_values)
        for index in range(period - 1, len(high_values)):
            start = index - period + 1
            highest = max(high_values[start:index + 1])
            lowest = min(low_values[start:index + 1])
            values[index] = (highest + lowest) / Decimal("2")
        return tuple(values)

    conversion = midpoint(conversion_period)
    base = midpoint(base_period)
    span_b = midpoint(span_b_period)
    span_a: list[Decimal | None] = [None] * len(high_values)
    for index, (conversion_value, base_value) in enumerate(zip(conversion, base)):
        if conversion_value is not None and base_value is not None:
            span_a[index] = (conversion_value + base_value) / Decimal("2")

    return IchimokuSeries(conversion, base, tuple(span_a), span_b)
