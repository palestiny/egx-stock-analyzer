from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Sequence


class SwingKind(StrEnum):
    HIGH = "high"
    LOW = "low"


@dataclass(frozen=True)
class SwingPoint:
    index: int
    kind: SwingKind
    price: Decimal


@dataclass(frozen=True)
class FibonacciExtension:
    ratio: Decimal
    price: Decimal


def detect_swing_points(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    *,
    left_bars: int = 2,
    right_bars: int = 2,
) -> tuple[SwingPoint, ...]:
    """Detect confirmed strict local pivots; the final right_bars observations are unconfirmed."""
    high_values, low_values = tuple(highs), tuple(lows)
    if len(high_values) != len(low_values):
        raise ValueError("highs and lows must have equal lengths")
    if left_bars < 1 or right_bars < 1:
        raise ValueError("left_bars and right_bars must be positive integers")
    for high, low in zip(high_values, low_values):
        if not high.is_finite() or not low.is_finite():
            raise ValueError("swing inputs must be finite Decimal values")
        if high < low:
            raise ValueError("each high must be greater than or equal to its low")

    pivots: list[SwingPoint] = []
    for index in range(left_bars, len(high_values) - right_bars):
        left = slice(index - left_bars, index)
        right = slice(index + 1, index + right_bars + 1)
        high = high_values[index]
        low = low_values[index]
        if all(high > value for value in (*high_values[left], *high_values[right])):
            pivots.append(SwingPoint(index, SwingKind.HIGH, high))
        if all(low < value for value in (*low_values[left], *low_values[right])):
            pivots.append(SwingPoint(index, SwingKind.LOW, low))

    return tuple(sorted(pivots, key=lambda point: (point.index, point.kind.value)))


def fibonacci_extensions(
    start_price: Decimal,
    end_price: Decimal,
    *,
    ratios: Sequence[Decimal] = (
        Decimal("1.0"),
        Decimal("1.272"),
        Decimal("1.618"),
        Decimal("2.0"),
        Decimal("2.618"),
    ),
) -> tuple[FibonacciExtension, ...]:
    """Project explicit swing-leg extension ratios from end_price in the leg's direction."""
    if not start_price.is_finite() or not end_price.is_finite():
        raise ValueError("swing prices must be finite Decimal values")
    leg = end_price - start_price
    if leg == 0:
        raise ValueError("swing leg must have non-zero length")
    normalized_ratios = tuple(ratios)
    if not normalized_ratios:
        raise ValueError("ratios cannot be empty")
    if any(not ratio.is_finite() or ratio <= 0 for ratio in normalized_ratios):
        raise ValueError("extension ratios must be finite and positive")
    if len(set(normalized_ratios)) != len(normalized_ratios):
        raise ValueError("extension ratios must be unique")

    return tuple(
        FibonacciExtension(ratio=ratio, price=end_price + leg * (ratio - Decimal("1")))
        for ratio in normalized_ratios
    )
