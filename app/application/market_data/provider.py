from datetime import date
from typing import Protocol

from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.stocks.stock import Stock


class MarketDataProvider(Protocol):
    def get_daily_observations(
        self,
        stock: Stock,
        from_date: date,
        to_date: date,
    ) -> list[RawPriceBarObservation]:
        ...
