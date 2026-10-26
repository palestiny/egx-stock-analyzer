from decimal import Decimal

from app.domain.technical_analysis.elliott import ElliottDirection, ElliottImpulseCandidate


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
