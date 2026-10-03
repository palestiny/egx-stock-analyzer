from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class MarketSnapshot:
    market: str
    timestamp: datetime
    index_value: Decimal | None
    index_change_percent: Decimal | None
    advancers: int
    decliners: int
    unchanged: int
    traded_value: Decimal | None
    active_symbols: int

    def __post_init__(self) -> None:
        if not self.market.strip():
            raise ValueError("market is required")
        if min(self.advancers, self.decliners, self.unchanged, self.active_symbols) < 0:
            raise ValueError("market counts cannot be negative")
        if self.advancers + self.decliners + self.unchanged > self.active_symbols:
            raise ValueError("market breadth cannot exceed active symbols")
        if self.traded_value is not None and self.traded_value < 0:
            raise ValueError("traded value cannot be negative")


@dataclass(frozen=True)
class MarketOverview:
    snapshot: MarketSnapshot
    breadth_ratio: Decimal | None
    breadth_status: str

    @staticmethod
    def from_snapshot(snapshot: MarketSnapshot) -> "MarketOverview":
        denominator = snapshot.advancers + snapshot.decliners
        ratio = (
            Decimal(snapshot.advancers) / Decimal(denominator)
            if denominator
            else None
        )
        if ratio is None:
            status = "UNDEFINED"
        elif ratio > Decimal("0.60"):
            status = "ADVANCERS_DOMINANT"
        elif ratio < Decimal("0.40"):
            status = "DECLINERS_DOMINANT"
        else:
            status = "BALANCED"
        return MarketOverview(snapshot=snapshot, breadth_ratio=ratio, breadth_status=status)
