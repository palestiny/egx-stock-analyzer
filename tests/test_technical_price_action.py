from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.technical_analysis.price_action import (
    CandlestickPattern,
    detect_candlestick_patterns,
    fibonacci_retracements,
)


def bar(open_price: str, high: str, low: str, close: str, day: int) -> PriceBar:
    return PriceBar.create(
        stock_id=uuid4(),
        timeframe=Timeframe.DAILY,
        timestamp=datetime(2026, 10, day, tzinfo=timezone.utc),
        open=Price(Decimal(open_price)),
        high=Price(Decimal(high)),
        low=Price(Decimal(low)),
        close=Price(Decimal(close)),
        volume=Volume(1000),
    )


def test_doji_is_reported_as_neutral_observation() -> None:
    result = detect_candlestick_patterns([bar("10", "11", "9", "10.05", 1)])
    assert len(result) == 1
    assert result[0][0].pattern is CandlestickPattern.DOJI
    assert result[0][0].bullish is None


def test_bullish_engulfing_requires_a_bearish_previous_candle() -> None:
    result = detect_candlestick_patterns([
        bar("10", "10.5", "8.5", "9", 1),
        bar("8.8", "11", "8", "10.7", 2),
    ])
    assert any(item.pattern is CandlestickPattern.BULLISH_ENGULFING for item in result[1])


def test_fibonacci_retracement_uses_explicit_up_swing_endpoints() -> None:
    levels = fibonacci_retracements(
        Decimal("100"), Decimal("200"), direction="up",
        ratios=(Decimal("0.5"), Decimal("0.618")),
    )
    assert levels.retracements == (
        (Decimal("0.5"), Decimal("150.0")),
        (Decimal("0.618"), Decimal("138.200")),
    )


def test_fibonacci_retracement_for_down_swing_is_measured_up_from_low() -> None:
    levels = fibonacci_retracements(
        Decimal("100"), Decimal("200"), direction="down",
        ratios=(Decimal("0.5"),),
    )
    assert levels.retracements == ((Decimal("0.5"), Decimal("150.0")),)


@pytest.mark.parametrize(
    ("low", "high", "direction"),
    [
        ("0", "10", "up"),
        ("10", "10", "up"),
        ("10", "9", "up"),
        ("10", "20", "sideways"),
    ],
)
def test_fibonacci_rejects_invalid_swing(low: str, high: str, direction: str) -> None:
    with pytest.raises(ValueError):
        fibonacci_retracements(Decimal(low), Decimal(high), direction=direction)


def test_candlestick_output_stays_aligned_to_input_bars() -> None:
    bars = [bar("10", "11", "9", "10.5", 1), bar("10.5", "12", "10", "11.5", 2)]
    assert len(detect_candlestick_patterns(bars)) == len(bars)


def test_hammer_requires_long_lower_wick_and_small_upper_wick() -> None:
    result = detect_candlestick_patterns([bar("10", "10.3", "7", "10.2", 3)])
    assert any(item.pattern is CandlestickPattern.HAMMER for item in result[0])


def test_bearish_engulfing_requires_a_bullish_previous_candle() -> None:
    result = detect_candlestick_patterns([
        bar("9", "10.5", "8.5", "10", 4),
        bar("10.2", "11", "8", "8.7", 5),
    ])
    assert any(item.pattern is CandlestickPattern.BEARISH_ENGULFING for item in result[1])
