from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.market_data.price import Price
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume


@dataclass(frozen=True)
class PriceBar:
    stock_id: UUID
    timeframe: Timeframe
    timestamp: datetime
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Volume

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("PriceBar timestamp must be timezone-aware")

    @classmethod
    def create(
        cls,
        stock_id: UUID,
        timeframe: Timeframe,
        timestamp: datetime,
        open: Price,
        high: Price,
        low: Price,
        close: Price,
        volume: Volume,
    ) -> "PriceBar":
        return cls(
            stock_id=stock_id,
            timeframe=timeframe,
            timestamp=timestamp,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )
