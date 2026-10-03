from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class BreakoutDirection(Enum):
    UPSIDE = "upside"
    DOWNSIDE = "downside"


class BreakoutStatus(Enum):
    CONFIRMED = "confirmed"
    CANDIDATE = "candidate"


@dataclass(frozen=True)
class BreakoutMatch:
    symbol: str
    direction: BreakoutDirection
    status: BreakoutStatus
    trigger_price: Decimal
    current_price: Decimal
    distance_percent: Decimal
    score: int
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.trigger_price <= 0 or self.current_price <= 0:
            raise ValueError("prices must be positive")
        if self.score < 0 or self.score > 100:
            raise ValueError("score must be between 0 and 100")


@dataclass(frozen=True)
class BreakoutScanResult:
    matches: tuple[BreakoutMatch, ...]
    evaluated_symbols: int
    data_status: str
