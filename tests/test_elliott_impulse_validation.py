from decimal import Decimal

from app.domain.technical_analysis.elliott import (\n    ElliottDirection,\n    ElliottImpulseCandidate,\n    enumerate_impulse_counts,\n)\nfrom app.domain.technical_analysis.price_structure import SwingKind, SwingPoint


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
