from datetime import date, datetime, timezone
from decimal import Decimal

from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.stocks.stock import Stock
from app.infrastructure.market_data.yahoo_finance import YahooFinanceAdapter


class FakeHistoryClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, date, date]] = []

    def history(self, ticker: str, start: date, end: date):
        self.calls.append((ticker, start, end))
        return [
            {
                "timestamp": datetime(2026, 1, 5, tzinfo=timezone.utc),
                "Open": Decimal("10.00"),
                "High": Decimal("11.00"),
                "Low": Decimal("9.50"),
                "Close": Decimal("10.50"),
                "Volume": 1000,
            }
        ]


def test_adapter_maps_egx_symbol_to_yahoo_symbol() -> None:
    client = FakeHistoryClient()
    adapter = YahooFinanceAdapter(client)
    stock = Stock.create("COMI", "Commercial International Bank")

    result = adapter.get_daily_observations(
        stock,
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert client.calls == [("COMI.CA", date(2026, 1, 1), date(2026, 1, 31))]
    assert len(result) == 1


def test_adapter_returns_raw_observations() -> None:
    client = FakeHistoryClient()
    adapter = YahooFinanceAdapter(client)
    stock = Stock.create("COMI", "Commercial International Bank")

    result = adapter.get_daily_observations(
        stock,
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert isinstance(result[0], RawPriceBarObservation)
    assert result[0].stock_id == stock.id
    assert result[0].open == Decimal("10.00")
    assert result[0].high == Decimal("11.00")
    assert result[0].low == Decimal("9.50")
    assert result[0].close == Decimal("10.50")
    assert result[0].volume == 1000


def test_adapter_does_not_create_price_bars() -> None:
    client = FakeHistoryClient()
    adapter = YahooFinanceAdapter(client)
    stock = Stock.create("COMI", "Commercial International Bank")

    result = adapter.get_daily_observations(
        stock,
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert all(type(item) is RawPriceBarObservation for item in result)


def test_adapter_mapping_is_deterministic() -> None:
    client = FakeHistoryClient()
    adapter = YahooFinanceAdapter(client)
    stock = Stock.create("COMI", "Commercial International Bank")

    first = adapter.get_daily_observations(stock, date(2026, 1, 1), date(2026, 1, 31))
    second = adapter.get_daily_observations(stock, date(2026, 1, 1), date(2026, 1, 31))

    assert first == second
