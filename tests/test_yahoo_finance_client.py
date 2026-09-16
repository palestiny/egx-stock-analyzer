from datetime import date

from app.infrastructure.market_data.yahoo_finance import YahooFinanceHistoryClient


class FakeHistory:
    def reset_index(self):
        return self

    def to_dict(self, orient: str):
        assert orient == "records"
        return [{"Date": date(2026, 1, 5)}]


class FakeTicker:
    def __init__(self) -> None:
        self.calls = []

    def history(self, **kwargs):
        self.calls.append(kwargs)
        return FakeHistory()


class FakeYFinance:
    def __init__(self) -> None:
        self.ticker = FakeTicker()

    def Ticker(self, symbol: str):
        self.last_symbol = symbol
        return self.ticker


def test_yahoo_history_client_requests_daily_history() -> None:
    fake_yfinance = FakeYFinance()
    client = YahooFinanceHistoryClient(fake_yfinance)

    result = client.history("COMI.CA", date(2026, 1, 1), date(2026, 1, 31))

    assert result == [{"Date": date(2026, 1, 5)}]
    assert fake_yfinance.last_symbol == "COMI.CA"
    assert fake_yfinance.ticker.calls == [
        {
            "start": date(2026, 1, 1),
            "end": date(2026, 1, 31),
            "interval": "1d",
            "auto_adjust": False,
        }
    ]
