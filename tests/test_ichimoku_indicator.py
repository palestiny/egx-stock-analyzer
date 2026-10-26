from decimal import Decimal

import pytest

from app.domain.technical_analysis.indicators import ichimoku_cloud


def d(*items: str) -> list[Decimal]:
    return [Decimal(item) for item in items]


def test_ichimoku_components_respect_each_period_and_keep_alignment() -> None:
    result = ichimoku_cloud(
        highs=d("10", "11", "12", "13", "14"),
        lows=d("8", "9", "10", "11", "12"),
        conversion_period=2,
        base_period=3,
        span_b_period=4,
    )
    assert result.conversion_line[0] is None
    assert result.conversion_line[1] == Decimal("9.5")
    assert result.base_line[1] is None
    assert result.base_line[2] == Decimal("10")
    assert result.leading_span_a_unshifted[1] is None
    assert result.leading_span_a_unshifted[2] is not None
    assert result.leading_span_b_unshifted[2] is None
    assert result.leading_span_b_unshifted[3] is not None


def test_ichimoku_rejects_misaligned_inputs() -> None:
    with pytest.raises(ValueError, match="equal lengths"):
        ichimoku_cloud(d("10", "11"), d("9"), conversion_period=1, base_period=1, span_b_period=1)
