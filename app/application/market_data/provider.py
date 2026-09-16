from datetime import date
from typing import Protocol, runtime_checkable

from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.stocks.stock import Stock


@runtime_checkable
class MarketDataProvider(Protocol):
    def get_daily_observations(
        self,
        stock: Stock,
        from_date: date,
        to_date: date,
    ) -> list[RawPriceBarObservation]:
        ...
