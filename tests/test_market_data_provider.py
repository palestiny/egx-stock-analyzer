from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.application.market_data.provider import MarketDataProvider
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock


class FakeMarketDataProvider:
    def __init__(self, observations: list[RawPriceBarObservation]) -> None:
        self.observations = observations
        self.calls: list[tuple[str, date, date]] = []

    def get_daily_observations(
        self,
        stock: Stock,
        from_date: date,
        to_date: date,
    ) -> list[RawPriceBarObservation]:
        self.calls.append((stock.symbol, from_date, to_date))
        return list(self.observations)


def test_fake_provider_satisfies_provider_port() -> None:
    assert isinstance(FakeMarketDataProvider([]), MarketDataProvider)


def test_provider_returns_raw_observations_for_requested_period() -> None:
    stock = Stock.create("COMI", "Commercial International Bank")
    observation = RawPriceBarObservation(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        timestamp=datetime(2026, 1, 5, tzinfo=timezone.utc),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        volume=1000,
    )
    provider = FakeMarketDataProvider([observation])

    result = provider.get_daily_observations(
        stock,
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert result == [observation]
    assert provider.calls == [("COMI", date(2026, 1, 1), date(2026, 1, 31))]


def test_provider_does_not_return_price_bars() -> None:
    provider = FakeMarketDataProvider([])
    result = provider.get_daily_observations(
        Stock.create("COMI", "Commercial International Bank"),
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert all(isinstance(item, RawPriceBarObservation) for item in result)


def test_provider_returns_deterministic_results() -> None:
    stock_id = uuid4()
    observation = RawPriceBarObservation(
        stock_id=stock_id,
        timeframe=Timeframe.DAILY,
        timestamp=datetime(2026, 1, 5, tzinfo=timezone.utc),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        volume=1000,
    )
    provider = FakeMarketDataProvider([observation])
    stock = Stock.create("COMI", "Commercial International Bank")

    first = provider.get_daily_observations(stock, date(2026, 1, 1), date(2026, 1, 31))
    second = provider.get_daily_observations(stock, date(2026, 1, 1), date(2026, 1, 31))

    assert first == second
