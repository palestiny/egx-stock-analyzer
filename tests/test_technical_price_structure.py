from decimal import Decimal

import pytest

from app.domain.technical_analysis.price_structure import (
    SwingKind,
    detect_swing_points,
)


def d(*values: str) -> tuple[Decimal, ...]:
    return tuple(Decimal(value) for value in values)


def test_detect_swing_points_requires_left_and_right_confirmation_bars() -> None:
    highs = d("10", "12", "15", "13", "11", "10")
    lows = d("8", "9", "10", "7", "8", "9")

    pivots = detect_swing_points(highs, lows, left_bars=1, right_bars=1)

    assert len(pivots) == 2
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

