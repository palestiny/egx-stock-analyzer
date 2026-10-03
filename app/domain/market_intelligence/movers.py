from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class MoverDirection(Enum):
    LEADER = "leader"
    LAGGARD = "laggard"


@dataclass(frozen=True)
class MarketMover:
    symbol: str
    direction: MoverDirection
    momentum_percent: Decimal
    score: int

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if not 0 <= self.score <= 100:
            raise ValueError("score must be between 0 and 100")


@dataclass(frozen=True)
class MarketMoverRanking:
    movers: tuple[MarketMover, ...]
    metric: str
    data_status: str

    def __post_init__(self) -> None:
        if not self.metric.strip():
            raise ValueError("metric is required")
        if not self.data_status.strip():
            raise ValueError("data_status is required")
