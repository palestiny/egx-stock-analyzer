from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.stocks.stock import Stock


# Tests that PriceBar represents the complete OHLCV market observation with its analysis context.
# This exists to protect the meaning and composition of the PriceBar Value Object.
# Its function is to verify that all supplied fields are preserved correctly.
def test_price_bar_represents_an_ohlcv_observation():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )
    timestamp = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)

    price_bar = PriceBar.create(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        timestamp=timestamp,
        open=Price(Decimal("100")),
        high=Price(Decimal("105")),
        low=Price(Decimal("98")),
        close=Price(Decimal("103")),
        volume=Volume(1_000_000),
    )

    assert price_bar.stock_id == stock.id
    assert price_bar.timeframe is Timeframe.DAILY
    assert price_bar.timestamp == timestamp
    assert price_bar.open == Price(Decimal("100"))
    assert price_bar.high == Price(Decimal("105"))
    assert price_bar.low == Price(Decimal("98"))
    assert price_bar.close == Price(Decimal("103"))
    assert price_bar.volume == Volume(1_000_000)


# Tests that PriceBar requires an explicit timezone-aware timestamp.
# This exists because market observations must have an unambiguous point in time.
# Its function is to reject naive datetimes that could be interpreted differently by different systems.
def test_price_bar_requires_timezone_aware_timestamp():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        PriceBar.create(
            stock_id=stock.id,
            timeframe=Timeframe.DAILY,
            timestamp=datetime(2026, 9, 6, 10, 0),
            open=Price(Decimal("100")),
            high=Price(Decimal("90")),
            low=Price(Decimal("95")),
            close=Price(Decimal("98")),
            volume=Volume(1_000_000),
        )


# Tests that PriceBar does not enforce provider/external OHLC relationships itself.
# This exists because external observations are data that must later be assessed by Data Quality, not silently rewritten or rejected here.
# Its function is to protect the boundary that PriceBar represents an observation without owning data-quality rules.
def test_price_bar_does_not_reject_external_ohlc_relationships():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    price_bar = PriceBar.create(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        timestamp=datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc),
        open=Price(Decimal("100")),
        high=Price(Decimal("90")),
        low=Price(Decimal("95")),
        close=Price(Decimal("98")),
        volume=Volume(1_000_000),
    )

    assert price_bar.high == Price(Decimal("90"))


# Tests that PriceBar is immutable after creation.
# This exists because PriceBar is a Value Object representing a historical observation that should not mutate.
# Its function is to protect the frozen Value Object contract.
def test_price_bar_is_immutable():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    price_bar = PriceBar.create(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        timestamp=datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc),
        open=Price(Decimal("100")),
        high=Price(Decimal("105")),
        low=Price(Decimal("98")),
        close=Price(Decimal("103")),
        volume=Volume(1_000_000),
    )

    with pytest.raises(AttributeError):
        price_bar.close = Price(Decimal("104"))
