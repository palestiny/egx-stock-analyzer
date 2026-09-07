from datetime import datetime, timezone

import pytest

from app.domain.stocks.stock import Stock
from app.domain.market_data.market_data import MarketData


def test_market_data_belongs_to_stock():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    timestamp = datetime(
        2026,
        9,
        6,
        10,
        0,
        tzinfo=timezone.utc,
    )

    market_data = MarketData.create(
        stock_id=stock.id,
        timestamp=timestamp,
        open=100,
        high=105,
        low=98,
        close=103,
        volume=1_000_000,
    )

    assert market_data.stock_id == stock.id

def test_market_data_rejects_high_below_open():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    timestamp = datetime(
        2026,
        9,
        6,
        10,
        0,
        tzinfo=timezone.utc,
    )

    with pytest.raises(ValueError):
        MarketData.create(
            stock_id=stock.id,
            timestamp=timestamp,
            open=100,
            high=90,      # ❌ High أقل من Open
            low=95,
            close=98,
            volume=1_000_000,
        )