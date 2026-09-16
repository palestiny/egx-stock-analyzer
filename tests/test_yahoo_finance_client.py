from datetime import date

from app.infrastructure.market_data.yahoo_finance import YahooFinanceHistoryClient


class FakeTicker:
    def __init__(self) -> None:
        self.calls = []

    def history(self, **kwargs):
        self.calls.append(kwargs)
        return "history-data"


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

    assert result == "history-data"
    assert fake_yfinance.last_symbol == "COMI.CA"
    assert fake_yfinance.ticker.calls == [
        {
            "start": date(2026, 1, 1),
            "end": date(2026, 1, 31),
            "interval": "1d",
            "auto_adjust": False,
        }
    ]
