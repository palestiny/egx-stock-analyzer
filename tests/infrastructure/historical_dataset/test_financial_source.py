from datetime import date
from pathlib import Path
from uuid import UUID

from app.application.fundamental_data.historical_provider import PointInTimeFundamentalDataProvider
from app.domain.stocks.stock import Stock
from app.infrastructure.historical_dataset.financial_source import HistoricalDatasetFundamentalSnapshotSource
from app.infrastructure.historical_dataset.loader import HistoricalDatasetLoader


FIXTURE = Path("tests/fixtures/historical_dataset/v1")
STOCK = Stock(UUID("00000000-0000-0000-0000-000000000001"), "TEST", "Test Stock")


def test_financial_source_reuses_point_in_time_provider_contract() -> None:
    source = HistoricalDatasetFundamentalSnapshotSource(HistoricalDatasetLoader(FIXTURE))
    provider = PointInTimeFundamentalDataProvider(source)

    current, previous = provider.get_periods(STOCK, date(2026, 3, 1))

    assert current.period_end == date(2025, 12, 31)
    assert previous.period_end == date(2024, 12, 31)
    assert str(current.revenue) == "1000000.00"
    assert str(previous.revenue) == "900000.00"
