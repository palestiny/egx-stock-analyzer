from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.market_data.timeframe import Timeframe


@dataclass(frozen=True)
class RawPriceBarObservation:
    stock_id: UUID | None
    timeframe: Timeframe | None
    timestamp: datetime | None
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    volume: int | None
