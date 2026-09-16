from datetime import date, datetime, timezone
from decimal import Decimal

from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock


class YahooFinanceHistoryClient:
    def __init__(self, yfinance_module) -> None:
        self._yfinance = yfinance_module

    def history(self, ticker: str, start: date, end: date) -> list[dict]:
        return (
            self._yfinance.Ticker(ticker)
            .history(
                start=start,
                end=end,
                interval="1d",
                auto_adjust=False,
            )
            .reset_index()
            .to_dict("records")
        )


class YahooFinanceAdapter:
    def __init__(self, history_client) -> None:
        self._history_client = history_client

    @staticmethod
    def _provider_symbol(stock: Stock) -> str:
        return f"{stock.symbol}.CA"

    @staticmethod
    def _timestamp(value) -> datetime:
        if isinstance(value, datetime):
            timestamp = value
        else:
            timestamp = datetime.combine(value, datetime.min.time())

        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            return timestamp.replace(tzinfo=timezone.utc)

        return timestamp

    @staticmethod
    def _decimal(value) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    def get_daily_observations(
        self,
        stock: Stock,
        from_date: date,
        to_date: date,
    ) -> list[RawPriceBarObservation]:
        rows = self._history_client.history(
            self._provider_symbol(stock),
            from_date,
            to_date,
        )

        return [
            RawPriceBarObservation(
                stock_id=stock.id,
                timeframe=Timeframe.DAILY,
                timestamp=self._timestamp(row["Date"]),
                open=self._decimal(row["Open"]),
                high=self._decimal(row["High"]),
                low=self._decimal(row["Low"]),
                close=self._decimal(row["Close"]),
                volume=None if row["Volume"] is None else int(row["Volume"]),
            )
            for row in rows
        ]
