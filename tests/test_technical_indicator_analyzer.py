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
