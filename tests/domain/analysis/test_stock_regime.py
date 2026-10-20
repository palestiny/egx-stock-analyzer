from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.analysis.stock_regime import (
    StockRegimeAnalyzer,
    TrendRegime,
    VolatilityRegime,
)
from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume


def _bars(closes: list[float]) -> list[PriceBar]:
    stock_id = uuid4()
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        PriceBar(
            stock_id=stock_id,
            timeframe=Timeframe.DAILY,
            timestamp=start + timedelta(days=index),
            open=Price(Decimal(str(close))),
            high=Price(Decimal(str(close * 1.01))),
            low=Price(Decimal(str(close * 0.99))),
            close=Price(Decimal(str(close))),
            volume=Volume(1000),
        )
        for index, close in enumerate(closes)
    ]


def test_upward_series_is_classified_as_uptrend() -> None:
    result = StockRegimeAnalyzer.analyze(_bars([100 + index for index in range(60)]))

    assert result.trend is TrendRegime.UPTREND
    assert result.observation_count == 60
    assert result.sma_20 is not None and result.sma_50 is not None
    assert result.annualized_realized_volatility is not None
    assert result.drawdown_from_observed_peak == 0


def test_downward_series_is_classified_as_downtrend() -> None:
    result = StockRegimeAnalyzer.analyze(_bars([200 - index for index in range(60)]))

    assert result.trend is TrendRegime.DOWNTREND
    assert result.drawdown_from_observed_peak < 0


def test_flat_series_has_low_volatility_and_sideways_trend() -> None:
    result = StockRegimeAnalyzer.analyze(_bars([100] * 60))

    assert result.trend is TrendRegime.SIDEWAYS
    assert result.volatility is VolatilityRegime.LOW
    assert result.annualized_realized_volatility == 0


def test_insufficient_history_does_not_invent_metrics() -> None:
    result = StockRegimeAnalyzer.analyze(_bars([100 + index for index in range(49)]))

    assert result.trend is TrendRegime.INSUFFICIENT_DATA
    assert result.volatility is VolatilityRegime.INSUFFICIENT_DATA
    assert result.sma_20 is None
    assert result.sma_50 is None
    assert result.annualized_realized_volatility is None
    assert result.drawdown_from_observed_peak is None


def test_rejects_unsorted_bars() -> None:
    bars = _bars([100, 101, 102])
    with pytest.raises(ValueError, match="strictly ordered"):
        StockRegimeAnalyzer.analyze([bars[1], bars[0], bars[2]])


def test_rejects_mixed_stocks() -> None:
    bars = _bars([100, 101])
    other_stock_bar = _bars([110])[0]
    with pytest.raises(ValueError, match="same stock and timeframe"):
        StockRegimeAnalyzer.analyze([bars[0], other_stock_bar])
