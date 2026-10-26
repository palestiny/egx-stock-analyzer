from decimal import Decimal

from app.domain.technical_analysis.indicators import average_directional_index


def d(*items: str) -> list[Decimal]:
    return [Decimal(item) for item in items]


def test_adx_and_directional_indicators_respect_warmup_and_bounds() -> None:
    result = average_directional_index(
        highs=d("10", "11", "12", "13", "14"),
        lows=d("8", "9", "10", "11", "12"),
        closes=d("9", "10", "11", "12", "13"),
        period=2,
    )
    assert result.plus_di[0] is None
    assert result.plus_di[1] is not None
    assert result.minus_di[1] is not None
    assert result.adx[0] is None
    assert result.adx[1] is None
    assert result.adx[2] is not None
    assert Decimal("0") <= result.adx[2] <= Decimal("100")


def test_adx_returns_missing_values_when_history_is_short() -> None:
    result = average_directional_index(
        highs=d("10"), lows=d("8"), closes=d("9"), period=14
    )
    assert result.plus_di == (None,)
    assert result.minus_di == (None,)
    assert result.adx == (None,)
