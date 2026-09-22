from datetime import date
from pathlib import Path
from uuid import UUID

from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock
from app.infrastructure.historical_dataset.loader import HistoricalDatasetLoader
from app.infrastructure.historical_dataset.market_provider import HistoricalDatasetMarketDataProvider


FIXTURE = Path("tests/fixtures/historical_dataset/v1")
STOCK = Stock(UUID("00000000-0000-0000-0000-000000000001"), "TEST", "Test Stock")


def test_market_provider_filters_by_stock_and_date_range() -> None:
    provider = HistoricalDatasetMarketDataProvider(HistoricalDatasetLoader(FIXTURE))

    rows = provider.get_daily_observations(STOCK, date(2026, 1, 6), date(2026, 1, 7))

    assert len(rows) == 2
    assert all(row.timeframe is Timeframe.DAILY for row in rows)
    assert [row.timestamp.date() for row in rows] == [date(2026, 1, 6), date(2026, 1, 7)]
    assert [row.volume for row in rows] == [1200, 900]


def test_market_provider_rejects_reversed_date_range() -> None:
    provider = HistoricalDatasetMarketDataProvider(HistoricalDatasetLoader(FIXTURE))

    try:
        provider.get_daily_observations(STOCK, date(2026, 1, 7), date(2026, 1, 6))
    except ValueError as exc:
        assert str(exc) == "from_date cannot be after to_date"
    else:
        raise AssertionError("Expected reversed date range to be rejected")
