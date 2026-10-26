from decimal import Decimal

import pytest

from app.domain.technical_analysis.indicators import (
    exponential_moving_average,
    simple_moving_average,
)


def d(*values: str) -> list[Decimal]:
    return [Decimal(value) for value in values]


def test_sma_aligns_results_and_waits_for_a_complete_window() -> None:
    assert simple_moving_average(d("1", "2", "3", "4", "5"), 3) == (
        None,
        None,
        Decimal("2"),
        Decimal("3"),
        Decimal("4"),
    )


def test_sma_returns_only_missing_values_when_history_is_too_short() -> None:
    assert simple_moving_average(d("2", "4"), 3) == (None, None)


def test_ema_is_seeded_with_first_complete_sma_window() -> None:
    assert exponential_moving_average(d("1", "2", "3", "4"), 3) == (
        None,
        None,
        Decimal("2"),
        Decimal("3"),
    )


def test_ema_returns_missing_values_when_history_is_too_short() -> None:
    assert exponential_moving_average(d("2", "4"), 3) == (None, None)


@pytest.mark.parametrize(
    "calculator",
    [simple_moving_average, exponential_moving_average],
)
def test_moving_average_rejects_non_positive_period(calculator) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        calculator(d("1", "2"), 0)


@pytest.mark.parametrize(
    "calculator",
    [simple_moving_average, exponential_moving_average],
)
def test_moving_average_rejects_non_finite_input(calculator) -> None:
    with pytest.raises(ValueError, match="finite Decimal"):
        calculator([Decimal("1"), Decimal("NaN")], 1)


def test_moving_average_handles_empty_history() -> None:
    assert simple_moving_average([], 2) == ()
    assert exponential_moving_average([], 2) == ()
