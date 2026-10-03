from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FibonacciOpportunity:
    symbol: str
    current_price: Decimal
    level: Decimal
    distance_percent: Decimal
    direction: str
    score: int

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.current_price <= 0 or self.level <= 0:
            raise ValueError("prices must be positive")
        if not 0 <= self.score <= 100:
            raise ValueError("score must be between 0 and 100")


@dataclass(frozen=True)
class FibonacciScanResult:
    opportunities: tuple[FibonacciOpportunity, ...]
    metric: str
    data_status: str
