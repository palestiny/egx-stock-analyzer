from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.application.market_intelligence.analyze_stock_regime import AnalyzeStockRegime
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock


class FakeMarketDataProvider:
    def __init__(self, observations: list[RawPriceBarObservation]) -> None:
        self.observations = observations
        self.request: tuple[date, date] | None = None

    def get_daily_observations(self, stock: Stock, from_date: date, to_date: date) -> list[RawPriceBarObservation]:
        self.request = (from_date, to_date)
        return [
            item for item in self.observations
            if item.stock_id == stock.id
            and item.timestamp is not None
            and from_date <= item.timestamp.date() <= to_date
        ]


def make_observations(stock: Stock, count: int) -> list[RawPriceBarObservation]:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    observations = []
    for index in range(count):
        close = Decimal(100 + index)
        observations.append(RawPriceBarObservation(
            stock_id=stock.id,
            timeframe=Timeframe.DAILY,
            timestamp=start + timedelta(days=index),
            open=close,
            high=close + Decimal("1"),
            low=close - Decimal("1"),
            close=close,
            volume=1000 + index,
        ))
    return observations


def test_analysis_uses_valid_bars_and_reports_provenance() -> None:
    stock = Stock.create("COMI", "Commercial International Bank")
    provider = FakeMarketDataProvider(make_observations(stock, 60))
    service = AnalyzeStockRegime(InMemoryStockCatalog([stock]), provider)
    result = service.execute(" comi ", as_of=date(2025, 4, 1))
    assert result.symbol == "COMI"
    assert result.source == "FakeMarketDataProvider"
    assert result.valid_observation_count == 60
    assert result.excluded_observation_count == 0
    assert result.latest_observation_date == date(2025, 3, 1)
    assert result.profile.trend.value == "uptrend"
    assert provider.request == (date(2023, 9, 29), date(2025, 4, 1))


def test_analysis_excludes_invalid_ohlc_observation() -> None:
    stock = Stock.create("COMI", "Commercial International Bank")
    observations = make_observations(stock, 60)
    item = observations[10]
    observations[10] = RawPriceBarObservation(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        timestamp=item.timestamp,
        open=Decimal("120"),
        high=Decimal("119"),
        low=Decimal("118"),
        close=Decimal("120"),
        volume=100,
    )
    result = AnalyzeStockRegime(
        InMemoryStockCatalog([stock]), FakeMarketDataProvider(observations)
    ).execute("COMI", as_of=date(2025, 4, 1))
    assert result.valid_observation_count == 59
    assert result.excluded_observation_count == 1


def test_analysis_rejects_unknown_symbol() -> None:
    service = AnalyzeStockRegime(InMemoryStockCatalog([]), FakeMarketDataProvider([]))
    with pytest.raises(ValueError, match="Unknown stock symbol: UNKNOWN"):
        service.execute("UNKNOWN", as_of=date(2025, 4, 1))
