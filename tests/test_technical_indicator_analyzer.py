from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.technical_analysis.indicator_analyzer import TechnicalIndicatorAnalyzer


def bars(count: int = 205) -> list[PriceBar]:
    stock_id = uuid4()
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    result = []
    for index in range(count):
        close = Decimal("100") + Decimal(index) / Decimal("10")
        result.append(PriceBar.create(
            stock_id=stock_id,
            timeframe=Timeframe.DAILY,
            timestamp=start + timedelta(days=index),
            open=Price(close - Decimal("0.1")),
            high=Price(close + Decimal("1")),
            low=Price(close - Decimal("1")),
            close=Price(close),
            volume=Volume(1000 + index),
        ))
    return result


def test_indicator_analyzer_returns_aligned_history_and_long_lookbacks() -> None:
    evidence = TechnicalIndicatorAnalyzer.analyze(bars())
    assert len(evidence.points) == 205
    assert evidence.points[0].sma_200 is None
    assert evidence.points[198].sma_200 is None
    assert evidence.points[199].sma_200 is not None
    assert evidence.latest is not None
    assert evidence.latest.ema_200 is not None
    assert evidence.latest.timestamp == bars()[-1].timestamp


def test_indicator_analyzer_rejects_unsorted_bars() -> None:
    sample = bars(3)
    with pytest.raises(ValueError, match="strictly ordered"):
        TechnicalIndicatorAnalyzer.analyze([sample[1], sample[0], sample[2]])


def test_indicator_analyzer_accepts_empty_history() -> None:
    assert TechnicalIndicatorAnalyzer.analyze([]).points == ()



def test_indicator_analyzer_includes_expanded_candlestick_pattern_evidence() -> None:
    stock_id = uuid4()
    timestamp = datetime(2026, 10, 26, tzinfo=timezone.utc)
    sample = [
        PriceBar.create(
            stock_id=stock_id,
            timeframe=Timeframe.DAILY,
            timestamp=timestamp,
            open=Price(Decimal("10")),
            high=Price(Decimal("10.2")),
            low=Price(Decimal("7.8")),
            close=Price(Decimal("8")),
            volume=Volume(1000),
        ),
        PriceBar.create(
            stock_id=stock_id,
            timeframe=Timeframe.DAILY,
            timestamp=timestamp + timedelta(days=1),
            open=Price(Decimal("7.5")),
            high=Price(Decimal("10.6")),
            low=Price(Decimal("7.3")),
            close=Price(Decimal("10.5")),
            volume=Volume(1500),
        ),
    ]

    evidence = TechnicalIndicatorAnalyzer.analyze(sample)

    assert "bullish_engulfing" in evidence.points[1].candlestick_patterns



def test_indicator_analyzer_exposes_swings_only_after_confirmation_and_fibonacci_anchors() -> None:
    stock_id = uuid4()
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    highs = (Decimal("10"), Decimal("12"), Decimal("15"), Decimal("13"), Decimal("11"), Decimal("10"))
    lows = (Decimal("8"), Decimal("9"), Decimal("10"), Decimal("7"), Decimal("8"), Decimal("9"))
    sample = []
    for index, (high, low) in enumerate(zip(highs, lows)):
        close = (high + low) / Decimal("2")
        sample.append(PriceBar.create(
            stock_id=stock_id,
            timeframe=Timeframe.DAILY,
            timestamp=start + timedelta(days=index),
            open=Price(close),
            high=Price(high),
            low=Price(low),
            close=Price(close),
            volume=Volume(1000),
        ))

    evidence = TechnicalIndicatorAnalyzer.analyze(sample)

    assert evidence.points[3].confirmed_swings == ()
    assert ("high", Decimal("15")) in evidence.points[4].confirmed_swings
    assert evidence.points[4].fibonacci_direction is None
    assert evidence.points[5].fibonacci_direction == "down"
    assert evidence.points[5].fibonacci_anchor_indices == (3, 2)
    assert len(evidence.points[5].fibonacci_retracements) == 5
