from decimal import Decimal

import pytest

from app.domain.technical_analysis.price_structure import (
    SwingKind,
    detect_swing_points,
    fibonacci_extensions,
)


def d(*values: str) -> tuple[Decimal, ...]:
    return tuple(Decimal(value) for value in values)


def test_detect_swing_points_requires_left_and_right_confirmation_bars() -> None:
    highs = d("10", "12", "15", "13", "11", "10")
    lows = d("8", "9", "10", "7", "8", "9")

    pivots = detect_swing_points(highs, lows, left_bars=1, right_bars=1)

    assert pivots == (
        # Both pivot types are allowed on different candles.
        pivots[0],
        pivots[1],
        pivots[2],
    )
    assert (pivots[0].index, pivots[0].kind, pivots[0].price) == (
        2,
        SwingKind.HIGH,
        Decimal("15"),
    )
    assert (pivots[1].index, pivots[1].kind, pivots[1].price) == (
        3,
        SwingKind.LOW,
        Decimal("7"),
    )
    assert all(p.index < len(highs) - 1 for p in pivots)


def test_swing_detection_rejects_mismatched_or_invalid_bars() -> None:
    with pytest.raises(ValueError, match="equal lengths"):
        detect_swing_points(d("1", "2"), d("1"))

    with pytest.raises(ValueError, match="positive integers"):
        detect_swing_points(d("1", "2"), d("1", "0"), left_bars=0)

    with pytest.raises(ValueError, match="finite Decimal"):
        detect_swing_points(d("1", "NaN"), d("0", "0"))


def test_fibonacci_extensions_project_in_the_direction_of_the_swing() -> None:
    ratios = d("1", "1.272", "1.618")

    up = fibonacci_extensions(Decimal("100"), Decimal("120"), ratios=ratios)
    down = fibonacci_extensions(Decimal("120"), Decimal("100"), ratios=ratios)

    assert tuple(level.price for level in up) == d("140", "145.440", "152.360")
    assert tuple(level.price for level in down) == d("80", "74.560", "67.640")


def test_fibonacci_extensions_reject_zero_leg_and_invalid_ratios() -> None:
    with pytest.raises(ValueError, match="non-zero length"):
        fibonacci_extensions(Decimal("10"), Decimal("10"))

    with pytest.raises(ValueError, match="finite and positive"):
        fibonacci_extensions(Decimal("10"), Decimal("11"), ratios=d("0"))

    with pytest.raises(ValueError, match="unique"):
        fibonacci_extensions(Decimal("10"), Decimal("11"), ratios=d("1", "1"))
