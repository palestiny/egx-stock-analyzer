from decimal import Decimal

from app.domain.technical_analysis.elliott import (
    ElliottDirection,
    ElliottImpulseCandidate,
    ElliottCorrectionCandidate,
    enumerate_impulse_counts,
    enumerate_zigzag_corrections,
)
from app.domain.technical_analysis.price_structure import SwingKind, SwingPoint


def d(*values: str) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]:
    return tuple(Decimal(value) for value in values)


def test_valid_up_impulse_candidate_passes_explicit_rules() -> None:
    candidate = ElliottImpulseCandidate(ElliottDirection.UP, d("100", "110", "105", "125", "118", "132"))
    assert candidate.is_rule_consistent
    assert candidate.rule_violations == ()


def test_invalid_wave_two_and_wave_four_are_reported() -> None:
    candidate = ElliottImpulseCandidate(ElliottDirection.UP, d("100", "110", "98", "120", "108", "125"))
    assert "wave_2_exceeds_origin" in candidate.rule_violations
    assert "wave_4_overlaps_wave_1_territory" in candidate.rule_violations


def test_valid_down_impulse_candidate_passes_explicit_rules() -> None:
    candidate = ElliottImpulseCandidate(ElliottDirection.DOWN, d("200", "180", "190", "150", "160", "140"))
    assert candidate.is_rule_consistent


def test_candidate_rejects_non_positive_prices() -> None:
    try:
        ElliottImpulseCandidate(ElliottDirection.UP, d("100", "110", "105", "125", "118", "0"))
    except ValueError as error:
        assert "positive prices" in str(error)
    else:
        raise AssertionError("Expected invalid price to be rejected")


def test_wave_two_may_retrace_exactly_to_origin_without_exceeding_it() -> None:
    candidate = ElliottImpulseCandidate(
        ElliottDirection.UP,
        d("100", "110", "100", "125", "118", "132"),
    )
    assert "wave_2_exceeds_origin" not in candidate.rule_violations


def test_truncated_fifth_is_reported_as_warning_not_hard_rule_violation() -> None:
    candidate = ElliottImpulseCandidate(
        ElliottDirection.UP,
        d("100", "110", "105", "125", "118", "125"),
    )
    assert candidate.is_rule_consistent
    assert candidate.warnings == ("possible_truncated_wave_5",)


def test_enumerates_upward_impulse_from_confirmed_alternating_swings() -> None:
    swings = (
        SwingPoint(0, SwingKind.LOW, Decimal("100")),
        SwingPoint(1, SwingKind.HIGH, Decimal("110")),
        SwingPoint(2, SwingKind.LOW, Decimal("105")),
        SwingPoint(3, SwingKind.HIGH, Decimal("125")),
        SwingPoint(4, SwingKind.LOW, Decimal("118")),
        SwingPoint(5, SwingKind.HIGH, Decimal("132")),
    )
    counts = enumerate_impulse_counts(swings)
    assert len(counts) == 1
    assert counts[0].candidate.direction is ElliottDirection.UP
    assert counts[0].is_rule_consistent
    assert counts[0].wave_two_invalidation_price == Decimal("100")
    assert (counts[0].start_index, counts[0].end_index) == (0, 5)


def test_enumerates_rule_inconsistent_alternative_with_diagnostics() -> None:
    swings = (
        SwingPoint(0, SwingKind.LOW, Decimal("100")),
        SwingPoint(1, SwingKind.HIGH, Decimal("110")),
        SwingPoint(2, SwingKind.LOW, Decimal("95")),
        SwingPoint(3, SwingKind.HIGH, Decimal("108")),
        SwingPoint(4, SwingKind.LOW, Decimal("99")),
        SwingPoint(5, SwingKind.HIGH, Decimal("112")),
    )
    counts = enumerate_impulse_counts(swings)
    assert len(counts) == 1
    assert not counts[0].is_rule_consistent
    assert "wave_2_exceeds_origin" in counts[0].rule_violations


def test_ignores_non_alternating_or_duplicate_index_windows() -> None:
    swings = (
        SwingPoint(0, SwingKind.LOW, Decimal("100")),
        SwingPoint(1, SwingKind.HIGH, Decimal("110")),
        SwingPoint(2, SwingKind.HIGH, Decimal("112")),
        SwingPoint(3, SwingKind.HIGH, Decimal("115")),
        SwingPoint(4, SwingKind.LOW, Decimal("105")),
        SwingPoint(5, SwingKind.HIGH, Decimal("120")),
    )
    assert enumerate_impulse_counts(swings) == ()


def test_rejects_unsorted_swing_points() -> None:
    swings = (
        SwingPoint(2, SwingKind.LOW, Decimal("100")),
        SwingPoint(1, SwingKind.HIGH, Decimal("110")),
    )
    try:
        enumerate_impulse_counts(swings)
    except ValueError as error:
        assert "ordered by index" in str(error)
    else:
        raise AssertionError("Expected unsorted swing points to be rejected")


def test_valid_downward_abc_zigzag_candidate_is_rule_consistent() -> None:
    candidate = ElliottCorrectionCandidate(
        ElliottDirection.DOWN,
        (Decimal("130"), Decimal("110"), Decimal("120"), Decimal("95")),
    )
    assert candidate.is_rule_consistent
    assert candidate.rule_violations == ()
    assert candidate.wave_b_origin_boundary_price == Decimal("130")


def test_valid_upward_abc_zigzag_candidate_is_rule_consistent() -> None:
    candidate = ElliottCorrectionCandidate(
        ElliottDirection.UP,
        (Decimal("80"), Decimal("100"), Decimal("90"), Decimal("108")),
    )
    assert candidate.is_rule_consistent


def test_abc_zigzag_candidate_exposes_beyond_origin_and_c_leg_violations() -> None:
    candidate = ElliottCorrectionCandidate(
        ElliottDirection.DOWN,
        (Decimal("130"), Decimal("110"), Decimal("132"), Decimal("112")),
    )
    assert "wave_b_exceeds_origin" in candidate.rule_violations
    assert "wave_c_does_not_extend_wave_a" in candidate.rule_violations


def test_enumerates_abc_zigzag_from_alternating_confirmed_swings() -> None:
    swings = (
        SwingPoint(10, SwingKind.HIGH, Decimal("130")),
        SwingPoint(12, SwingKind.LOW, Decimal("110")),
        SwingPoint(15, SwingKind.HIGH, Decimal("120")),
        SwingPoint(18, SwingKind.LOW, Decimal("95")),
    )
    counts = enumerate_zigzag_corrections(swings)
    assert len(counts) == 1
    assert counts[0].candidate.direction is ElliottDirection.DOWN
    assert counts[0].is_rule_consistent
    assert (counts[0].start_index, counts[0].end_index) == (10, 18)


def test_ignores_non_alternating_correction_windows() -> None:
    swings = (
        SwingPoint(0, SwingKind.HIGH, Decimal("130")),
        SwingPoint(1, SwingKind.LOW, Decimal("110")),
        SwingPoint(2, SwingKind.LOW, Decimal("105")),
        SwingPoint(3, SwingKind.HIGH, Decimal("120")),
    )
    assert enumerate_zigzag_corrections(swings) == ()
