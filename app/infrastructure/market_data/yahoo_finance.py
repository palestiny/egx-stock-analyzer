from datetime import date

from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock


class YahooFinanceAdapter:
    def __init__(self, history_client) -> None:
        self._history_client = history_client

    @staticmethod
    def _provider_symbol(stock: Stock) -> str:
        return f"{stock.symbol}.CA"

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
                timestamp=row["timestamp"],
                open=row["Open"],
                high=row["High"],
                low=row["Low"],
                close=row["Close"],
                volume=row["Volume"],
            )
            for row in rows
        ]
