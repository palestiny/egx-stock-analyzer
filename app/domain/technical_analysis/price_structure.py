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
