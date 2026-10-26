from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from collections.abc import Sequence


class PatternDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class CandlestickPattern(StrEnum):
    DOJI = "doji"
    HAMMER = "hammer"
    SHOOTING_STAR = "shooting_star"
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"
    BULLISH_HARAMI = "bullish_harami"
    BEARISH_HARAMI = "bearish_harami"
    PIERCING_LINE = "piercing_line"
    DARK_CLOUD_COVER = "dark_cloud_cover"
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    THREE_BLACK_CROWS = "three_black_crows"


@dataclass(frozen=True)
class CandlestickPatternEvidence:
    index: int
    pattern: CandlestickPattern
    direction: PatternDirection
    rule_version: str = "candles-v1"
    requires_context_confirmation: bool = True


def detect_candlestick_patterns(
    opens: Sequence[Decimal],
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    closes: Sequence[Decimal],
    *,
    doji_body_fraction: Decimal = Decimal("0.10"),
) -> tuple[CandlestickPatternEvidence, ...]:
    """Detect deterministic OHLC candle shapes; patterns are evidence, not standalone trade signals."""
    open_values, high_values, low_values, close_values = (
        tuple(opens), tuple(highs), tuple(lows), tuple(closes)
    )
    if not (len(open_values) == len(high_values) == len(low_values) == len(close_values)):
        raise ValueError("OHLC inputs must have equal lengths")
    if not doji_body_fraction.is_finite() or not (
        Decimal("0") <= doji_body_fraction <= Decimal("1")
    ):
        raise ValueError("doji_body_fraction must be between zero and one")

    for opn, high, low, close in zip(open_values, high_values, low_values, close_values):
        if any(not value.is_finite() for value in (opn, high, low, close)):
            raise ValueError("OHLC inputs must be finite Decimal values")
        if low > high or low > min(opn, close) or high < max(opn, close):
            raise ValueError("OHLC bounds are inconsistent")

    matches: list[CandlestickPatternEvidence] = []
    count = len(open_values)
    bodies = tuple(abs(close - opn) for opn, close in zip(open_values, close_values))
    ranges = tuple(high - low for high, low in zip(high_values, low_values))

    def bullish(i: int) -> bool:
        return close_values[i] > open_values[i]

    def bearish(i: int) -> bool:
        return close_values[i] < open_values[i]

    def add(i: int, pattern: CandlestickPattern, direction: PatternDirection) -> None:
        matches.append(CandlestickPatternEvidence(i, pattern, direction))

    for i in range(count):
        body, candle_range = bodies[i], ranges[i]
        if candle_range > 0 and body <= candle_range * doji_body_fraction:
            add(i, CandlestickPattern.DOJI, PatternDirection.NEUTRAL)
        if candle_range > 0 and body > 0:
            lower_wick = min(open_values[i], close_values[i]) - low_values[i]
            upper_wick = high_values[i] - max(open_values[i], close_values[i])
            if lower_wick >= body * 2 and upper_wick <= body:
                add(i, CandlestickPattern.HAMMER, PatternDirection.BULLISH)
            if upper_wick >= body * 2 and lower_wick <= body:
                add(i, CandlestickPattern.SHOOTING_STAR, PatternDirection.BEARISH)

    for i in range(1, count):
        prev_body, body = bodies[i - 1], bodies[i]
        if (
            bearish(i - 1) and bullish(i)
            and open_values[i] <= close_values[i - 1]
            and close_values[i] >= open_values[i - 1]
            and body > 0 and prev_body > 0
        ):
            add(i, CandlestickPattern.BULLISH_ENGULFING, PatternDirection.BULLISH)
        if (
            bullish(i - 1) and bearish(i)
            and open_values[i] >= close_values[i - 1]
            and close_values[i] <= open_values[i - 1]
            and body > 0 and prev_body > 0
        ):
            add(i, CandlestickPattern.BEARISH_ENGULFING, PatternDirection.BEARISH)
        if prev_body > 0 and body > 0:
            if (
                bearish(i - 1) and bullish(i)
                and open_values[i] >= close_values[i - 1]
                and close_values[i] <= open_values[i - 1]
            ):
                add(i, CandlestickPattern.BULLISH_HARAMI, PatternDirection.BULLISH)
            if (
                bullish(i - 1) and bearish(i)
                and open_values[i] <= close_values[i - 1]
                and close_values[i] >= open_values[i - 1]
            ):
                add(i, CandlestickPattern.BEARISH_HARAMI, PatternDirection.BEARISH)

        midpoint = (open_values[i - 1] + close_values[i - 1]) / Decimal("2")
        if (
            bearish(i - 1) and bullish(i)
            and open_values[i] < close_values[i - 1]
            and close_values[i] > midpoint
            and close_values[i] < open_values[i - 1]
        ):
            add(i, CandlestickPattern.PIERCING_LINE, PatternDirection.BULLISH)
        if (
            bullish(i - 1) and bearish(i)
            and open_values[i] > close_values[i - 1]
            and close_values[i] < midpoint
            and close_values[i] > open_values[i - 1]
        ):
            add(i, CandlestickPattern.DARK_CLOUD_COVER, PatternDirection.BEARISH)

    for i in range(2, count):
        first, middle, last = i - 2, i - 1, i
        midpoint_first = (open_values[first] + close_values[first]) / Decimal("2")
        midpoint_last = (open_values[last] + close_values[last]) / Decimal("2")
        small_middle = bodies[middle] <= bodies[first] * Decimal("0.5")
        if (
            bearish(first) and small_middle and bullish(last)
            and close_values[last] > midpoint_first
            and close_values[last] < open_values[first]
            and close_values[middle] <= close_values[first]
        ):
            add(last, CandlestickPattern.MORNING_STAR, PatternDirection.BULLISH)
        if (
            bullish(first) and small_middle and bearish(last)
            and close_values[last] < midpoint_first
            and close_values[last] > open_values[first]
            and close_values[middle] >= close_values[first]
        ):
            add(last, CandlestickPattern.EVENING_STAR, PatternDirection.BEARISH)

        if (
            bullish(first) and bullish(middle) and bullish(last)
            and close_values[first] < close_values[middle] < close_values[last]
            and open_values[middle] >= open_values[first]
            and open_values[middle] <= close_values[first]
            and open_values[last] >= open_values[middle]
            and open_values[last] <= close_values[middle]
        ):
            add(last, CandlestickPattern.THREE_WHITE_SOLDIERS, PatternDirection.BULLISH)
        if (
            bearish(first) and bearish(middle) and bearish(last)
            and close_values[first] > close_values[middle] > close_values[last]
            and open_values[middle] <= open_values[first]
            and open_values[middle] >= close_values[first]
            and open_values[last] <= open_values[middle]
            and open_values[last] >= close_values[middle]
        ):
            add(last, CandlestickPattern.THREE_BLACK_CROWS, PatternDirection.BEARISH)

    return tuple(sorted(matches, key=lambda match: (match.index, match.pattern.value)))
