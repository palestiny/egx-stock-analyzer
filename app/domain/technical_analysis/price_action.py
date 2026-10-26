from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.domain.market_data.price_bar import PriceBar


class CandlestickPattern(StrEnum):
    DOJI = "doji"
    HAMMER = "hammer"
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"


@dataclass(frozen=True)
class CandlestickEvidence:
    pattern: CandlestickPattern
    timestamp: datetime
    bullish: bool | None
    body_to_range: Decimal


def detect_candlestick_patterns(
    bars: tuple[PriceBar, ...] | list[PriceBar],
    *,
    doji_body_ratio: Decimal = Decimal("0.1"),
    hammer_body_to_range_max: Decimal = Decimal("0.35"),
    hammer_lower_wick_body_min: Decimal = Decimal("2"),
) -> tuple[tuple[CandlestickEvidence, ...], ...]:
    """Return index-aligned candle evidence; patterns are observations, not trade signals."""
    for name, value in (
        ("doji_body_ratio", doji_body_ratio),
        ("hammer_body_to_range_max", hammer_body_to_range_max),
        ("hammer_lower_wick_body_min", hammer_lower_wick_body_min),
    ):
        if not value.is_finite() or value < 0:
            raise ValueError(f"{name} must be a finite non-negative Decimal")
    if doji_body_ratio > 1 or hammer_body_to_range_max > 1:
        raise ValueError("body ratio thresholds must not exceed one")

    result: list[tuple[CandlestickEvidence, ...]] = []
    previous: PriceBar | None = None
    for bar in bars:
        open_price = bar.open.value
        close_price = bar.close.value
        high = bar.high.value
        low = bar.low.value
        candle_range = high - low
        body = abs(close_price - open_price)
        evidence: list[CandlestickEvidence] = []
        if candle_range <= 0:
            result.append(())
            previous = bar
            continue

        body_ratio = body / candle_range
        lower_wick = min(open_price, close_price) - low
        if body_ratio <= doji_body_ratio:
            evidence.append(CandlestickEvidence(
                CandlestickPattern.DOJI, bar.timestamp, None, body_ratio
            ))
        if (
            body_ratio <= hammer_body_to_range_max
            and body > 0
            and lower_wick >= body * hammer_lower_wick_body_min
            and (high - max(open_price, close_price)) <= body
        ):
            evidence.append(CandlestickEvidence(
                CandlestickPattern.HAMMER, bar.timestamp, close_price >= open_price, body_ratio
            ))

        if previous is not None:
            previous_open = previous.open.value
            previous_close = previous.close.value
            previous_bearish = previous_close < previous_open
            previous_bullish = previous_close > previous_open
            current_bullish = close_price > open_price
            current_bearish = close_price < open_price
            if (
                previous_bearish and current_bullish
                and open_price <= previous_close and close_price >= previous_open
            ):
                evidence.append(CandlestickEvidence(
                    CandlestickPattern.BULLISH_ENGULFING, bar.timestamp, True, body_ratio
                ))
            if (
                previous_bullish and current_bearish
                and open_price >= previous_close and close_price <= previous_open
            ):
                evidence.append(CandlestickEvidence(
                    CandlestickPattern.BEARISH_ENGULFING, bar.timestamp, False, body_ratio
                ))

        result.append(tuple(evidence))
        previous = bar
    return tuple(result)


@dataclass(frozen=True)
class FibonacciLevels:
    swing_low: Decimal
    swing_high: Decimal
    direction: str
    retracements: tuple[tuple[Decimal, Decimal], ...]


DEFAULT_FIBONACCI_RATIOS = (
    Decimal("0.236"),
    Decimal("0.382"),
    Decimal("0.5"),
    Decimal("0.618"),
    Decimal("0.786"),
)


def fibonacci_retracements(
    swing_low: Decimal,
    swing_high: Decimal,
    *,
    direction: str,
    ratios: tuple[Decimal, ...] = DEFAULT_FIBONACCI_RATIOS,
) -> FibonacciLevels:
    """Calculate retracement prices for explicit swing endpoints; never infer the swing."""
    if not swing_low.is_finite() or not swing_high.is_finite():
        raise ValueError("swing prices must be finite Decimal values")
    if swing_low <= 0 or swing_high <= swing_low:
        raise ValueError("swing prices must be positive and swing_high must exceed swing_low")
    if direction not in {"up", "down"}:
        raise ValueError("direction must be 'up' or 'down'")
    if not ratios:
        raise ValueError("at least one Fibonacci ratio is required")
    if any(not ratio.is_finite() or ratio <= 0 or ratio >= 1 for ratio in ratios):
        raise ValueError("Fibonacci ratios must be finite and strictly between zero and one")

    swing_range = swing_high - swing_low
    levels = tuple(
        (
            ratio,
            swing_high - swing_range * ratio
            if direction == "up"
            else swing_low + swing_range * ratio,
        )
        for ratio in ratios
    )
    return FibonacciLevels(swing_low, swing_high, direction, levels)
