from decimal import Decimal

from app.domain.technical_analysis.indicators import (
    commodity_channel_index,
    stochastic_oscillator,
)


def values(*items: str) -> list[Decimal]:
    return [Decimal(item) for item in items]


def test_stochastic_oscillator_produces_aligned_k_and_d_series() -> None:
    result = stochastic_oscillator(
        highs=values("10", "11", "12", "12"),
        lows=values("8", "9", "10", "10"),
        closes=values("9", "10", "11", "11"),
        k_period=2,
        d_period=2,
    )
    assert result.percent_k[0] is None
    assert result.percent_k[1] is not None
    assert result.percent_d[1] is None
    assert result.percent_d[2] is not None


def test_stochastic_flat_window_is_not_reported_as_neutral() -> None:
    result = stochastic_oscillator(
        highs=values("10", "10"),
        lows=values("10", "10"),
        closes=values("10", "10"),
        k_period=2,
        d_period=1,
    )
    assert result.percent_k[1] is None
    assert result.percent_d[1] is None


def test_cci_marks_constant_typical_price_window_unavailable() -> None:
    assert commodity_channel_index(
        highs=values("10", "10", "10"),
        lows=values("10", "10", "10"),
        closes=values("10", "10", "10"),
        period=3,
    ) == (None, None, None)
