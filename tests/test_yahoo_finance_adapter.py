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
                "Date": date(2026, 1, 5),
                "Open": 10.0,
                "High": 11.0,
                "Low": 9.5,
                "Close": 10.5,
                "Volume": 1000.0,
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


def test_adapter_normalizes_daily_timestamp_to_timezone_aware_datetime() -> None:
    result = YahooFinanceAdapter(FakeHistoryClient()).get_daily_observations(
        Stock.create("COMI", "Commercial International Bank"),
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert result[0].timestamp == datetime(2026, 1, 5, tzinfo=timezone.utc)


def test_adapter_normalizes_numeric_values_to_domain_types() -> None:
    result = YahooFinanceAdapter(FakeHistoryClient()).get_daily_observations(
        Stock.create("COMI", "Commercial International Bank"),
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert result[0].open == Decimal("10.0")
    assert result[0].high == Decimal("11.0")
    assert result[0].low == Decimal("9.5")
    assert result[0].close == Decimal("10.5")
    assert result[0].volume == 1000


def test_adapter_returns_raw_observations() -> None:
    result = YahooFinanceAdapter(FakeHistoryClient()).get_daily_observations(
        Stock.create("COMI", "Commercial International Bank"),
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert isinstance(result[0], RawPriceBarObservation)
    assert result[0].stock_id is not None
    assert result[0].open == Decimal("10.0")


def test_adapter_does_not_create_price_bars() -> None:
    result = YahooFinanceAdapter(FakeHistoryClient()).get_daily_observations(
        Stock.create("COMI", "Commercial International Bank"),
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert all(type(item) is RawPriceBarObservation for item in result)


def test_adapter_mapping_is_deterministic() -> None:
    adapter = YahooFinanceAdapter(FakeHistoryClient())
    stock = Stock.create("COMI", "Commercial International Bank")

    first = adapter.get_daily_observations(stock, date(2026, 1, 1), date(2026, 1, 31))
    second = adapter.get_daily_observations(stock, date(2026, 1, 1), date(2026, 1, 31))

    assert first == second
