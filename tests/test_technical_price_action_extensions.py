from decimal import Decimal

import pytest

from app.domain.technical_analysis.price_action_extensions import (
    fibonacci_extensions,
    session_vwap,
)


def d(*values: str) -> list[Decimal]:
    return [Decimal(value) for value in values]


def test_fibonacci_extensions_project_upward_from_explicit_pullback() -> None:
    result = fibonacci_extensions(
        Decimal("100"),
        Decimal("150"),
        Decimal("130"),
        direction="up",
        ratios=(Decimal("1"), Decimal("1.618")),
    )
    assert result.levels == (
        (Decimal("1"), Decimal("180")),
        (Decimal("1.618"), Decimal("210.90")),
    )


def test_fibonacci_extensions_project_downward_from_explicit_pullback() -> None:
    result = fibonacci_extensions(
        Decimal("150"),
        Decimal("100"),
        Decimal("120"),
        direction="down",
        ratios=(Decimal("1"),),
    )
    assert result.levels == ((Decimal("1"), Decimal("70")),)


@pytest.mark.parametrize(
    "args, message",
    [
        ((Decimal("100"), Decimal("100"), Decimal("90")), "upward impulse"),
        ((Decimal("100"), Decimal("150"), Decimal("160")), "pullback_end"),
        ((Decimal("0"), Decimal("150"), Decimal("120")), "positive"),
    ],
)
def test_fibonacci_extensions_reject_invalid_swings(args, message) -> None:
    with pytest.raises(ValueError, match=message):
        fibonacci_extensions(*args, direction="up")


def test_session_vwap_accumulates_within_session_and_resets_between_sessions() -> None:
    result = session_vwap(
        highs=d("12", "15", "20"),
        lows=d("10", "13", "18"),
        closes=d("11", "14", "19"),
        volumes=[10, 30, 20],
        session_ids=["2026-10-26", "2026-10-26", "2026-10-27"],
    )
    assert result == (
        Decimal("11"),
        Decimal("13.25"),
        Decimal("19"),
    )


def test_session_vwap_returns_none_for_zero_volume_until_volume_arrives() -> None:
    result = session_vwap(
        highs=d("12", "15"),
        lows=d("10", "13"),
        closes=d("11", "14"),
        volumes=[0, 10],
        session_ids=["s1", "s1"],
    )
    assert result == (None, Decimal("14"))


def test_session_vwap_rejects_misaligned_data_and_negative_volume() -> None:
    with pytest.raises(ValueError, match="equal lengths"):
        session_vwap(d("12"), d("10"), d("11"), [10, 20], ["s1"])
    with pytest.raises(ValueError, match="non-negative integers"):
        session_vwap(d("12"), d("10"), d("11"), [-1], ["s1"])


def test_session_vwap_rejects_close_outside_high_low_range() -> None:
    with pytest.raises(ValueError, match="close must be within"):
        session_vwap(
            highs=d("12"),
            lows=d("10"),
            closes=d("13"),
            volumes=[10],
            session_ids=["s1"],
        )


def test_session_vwap_rejects_non_contiguous_session_order() -> None:
    with pytest.raises(ValueError, match="contiguous"):
        session_vwap(
            highs=d("12", "15", "14"),
            lows=d("10", "13", "12"),
            closes=d("11", "14", "13"),
            volumes=[10, 20, 30],
            session_ids=["s1", "s2", "s1"],
        )
