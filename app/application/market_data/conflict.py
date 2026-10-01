from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.market_data.raw_observation import RawPriceBarObservation


@dataclass(frozen=True)
class MarketDataConflictEvent:
    conflict_id: UUID
    stock_id: UUID
    timeframe: str
    timestamp: datetime
    acquisition_id: UUID
    detected_at: datetime
    existing_acquisition_id: UUID | None
    existing_observation: RawPriceBarObservation
    incoming_observation: RawPriceBarObservation
