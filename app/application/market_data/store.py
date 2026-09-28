from datetime import date
from typing import Protocol
from uuid import UUID

from app.domain.market_data.raw_observation import RawPriceBarObservation


class OperationalMarketDataStore(Protocol):
    def get_daily_observations(
        self,
        stock_id: UUID,
        from_date: date,
        to_date: date,
    ) -> list[RawPriceBarObservation]:
        ...

    def save(self, observations: list[RawPriceBarObservation]) -> None:
        ...
