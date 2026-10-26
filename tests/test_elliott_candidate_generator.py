from decimal import Decimal

import pytest

from app.domain.technical_analysis.elliott_candidate_generator import (
    generate_elliott_impulse_candidates,
)
from app.domain.technical_analysis.price_structure import SwingKind, SwingPoint


def swings(values: tuple[str, ...], kinds: tuple[SwingKind, ...]):
    return tuple(
        SwingPoint(index=index * 2, kind=kind, price=Decimal(value))
        for index, (value, kind) in enumerate(zip(values, kinds))
    )


def test_generator_finds_rule_consistent_upward_impulse_without_probability() -> None:
    points = swings(
        ("100", "120", "110", "140", "130", "150"),
        (
            SwingKind.LOW, SwingKind.HIGH, SwingKind.LOW,
            SwingKind.HIGH, SwingKind.LOW, SwingKind.HIGH,
        ),
    )

    candidates = generate_elliott_impulse_candidates(points)

    assert len(candidates) == 1
    assert candidates[0].candidate.is_rule_consistent
    assert candidates[0].swing_indices == (0, 2, 4, 6, 8, 10)
    assert candidates[0].invalidation_level == Decimal("100")
    assert not hasattr(candidates[0], "probability")


def test_generator_finds_rule_consistent_downward_impulse() -> None:
    points = swings(
        ("150", "130", "140", "110", "120", "100"),
        (
            SwingKind.HIGH, SwingKind.LOW, SwingKind.HIGH,
            SwingKind.LOW, SwingKind.HIGH, SwingKind.LOW,
        ),
    )

    candidates = generate_elliott_impulse_candidates(points)

    assert len(candidates) == 1
    assert candidates[0].candidate.is_rule_consistent
    assert candidates[0].invalidation_level == Decimal("150")


def test_generator_excludes_rule_violations_and_non_alternating_pivots() -> None:
    invalid_wave = swings(
        ("100", "120", "115", "125", "121", "135"),
        (
            SwingKind.LOW, SwingKind.HIGH, SwingKind.LOW,
            SwingKind.HIGH, SwingKind.LOW, SwingKind.HIGH,
        ),
    )
    non_alternating = swings(
        ("100", "120", "110", "140", "130", "150"),
        (
            SwingKind.LOW, SwingKind.HIGH, SwingKind.LOW,
            SwingKind.HIGH, SwingKind.HIGH, SwingKind.HIGH,
        ),
    )

    assert generate_elliott_impulse_candidates(invalid_wave) == ()
    assert generate_elliott_impulse_candidates(non_alternating) == ()


def test_generator_rejects_unordered_swing_points() -> None:
    points = (
        SwingPoint(2, SwingKind.LOW, Decimal("100")),
        SwingPoint(1, SwingKind.HIGH, Decimal("120")),
    )
    with pytest.raises(ValueError, match="strictly ordered"):
        generate_elliott_impulse_candidates(points)
