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


from app.domain.technical_analysis.indicators import macd, relative_strength_index


def test_rsi_returns_none_during_warmup_and_one_hundred_for_only_gains() -> None:
    values = d("1", "2", "3", "4", "5")
    assert relative_strength_index(values, 3) == (
        None,
        None,
        None,
        Decimal("100"),
        Decimal("100"),
    )


def test_rsi_is_fifty_when_all_changes_are_zero() -> None:
    assert relative_strength_index(d("5", "5", "5", "5"), 3) == (
        None,
        None,
        None,
        Decimal("50"),
    )


def test_rsi_is_zero_when_average_gain_is_zero() -> None:
    assert relative_strength_index(d("5", "4", "3", "2"), 3) == (
        None,
        None,
        None,
        Decimal("0"),
    )


def test_macd_keeps_line_signal_and_histogram_index_aligned() -> None:
    values = d("1", "2", "3", "4", "5", "6", "7", "8")
    result = macd(values, fast_period=2, slow_period=3, signal_period=2)
    assert len(result.line) == len(values)
    assert len(result.signal) == len(values)
    assert len(result.histogram) == len(values)
    assert result.line[:2] == (None, None)
    assert result.signal[:3] == (None, None, None)
    assert result.histogram[:3] == (None, None, None)
    assert result.signal[3] is not None
    assert result.histogram[3] is not None


def test_macd_rejects_fast_period_not_less_than_slow_period() -> None:
    with pytest.raises(ValueError, match="fast_period"):
        macd(d("1", "2", "3"), fast_period=3, slow_period=3, signal_period=2)


def test_rsi_returns_missing_values_when_history_is_too_short() -> None:
    assert relative_strength_index(d("1", "2", "3"), 3) == (None, None, None)
