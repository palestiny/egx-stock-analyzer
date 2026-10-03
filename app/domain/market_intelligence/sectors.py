from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class SectorDirection(Enum):
    LEADING = "leading"
    LAGGING = "lagging"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class SectorSnapshot:
    sector: str
    symbol_count: int
    average_momentum_percent: Decimal
    average_score: Decimal

    def __post_init__(self) -> None:
        if not self.sector.strip():
            raise ValueError("sector is required")
        if self.symbol_count < 0:
            raise ValueError("symbol_count cannot be negative")
        if not 0 <= self.average_score <= 100:
            raise ValueError("average_score must be between 0 and 100")


@dataclass(frozen=True)
class SectorRanking:
    sectors: tuple[SectorSnapshot, ...]
    direction: SectorDirection
    metric: str
    data_status: str
