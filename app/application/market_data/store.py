from datetime import date
from typing import Protocol
from uuid import UUID

from app.application.market_data.acquisition import AcquisitionRecord
from app.application.market_data.conflict import MarketDataConflictEvent
from app.domain.market_data.raw_observation import RawPriceBarObservation


class OperationalMarketDataStore(Protocol):
    def get_daily_observations(
        self,
        stock_id: UUID,
        from_date: date,
        to_date: date,
    ) -> list[RawPriceBarObservation]:
        ...

    def persist_successful_acquisition(
        self,
        record: AcquisitionRecord,
        observations: list[RawPriceBarObservation],
    ) -> None:
        ...

    def save_acquisition(self, record: AcquisitionRecord) -> None:
        ...

    def get_acquisitions(
        self,
        stock_id: UUID,
        from_date: date,
        to_date: date,
    ) -> list[AcquisitionRecord]:
        ...

    def get_conflict_events(
        self,
        stock_id: UUID,
        from_date: date,
        to_date: date,
    ) -> list[MarketDataConflictEvent]:
        ...
