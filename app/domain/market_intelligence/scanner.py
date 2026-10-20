from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class ScannerCriterion(Enum):
    UPTREND = "uptrend"
    POSITIVE_MOMENTUM = "positive_momentum"
    ABOVE_AVERAGE_VOLUME = "above_average_volume"
    ACTIONABLE_CLASSIFICATION = "actionable_classification"
    VOLUME_EXPANSION = "volume_expansion"
    NEAR_RESISTANCE = "near_resistance"


@dataclass(frozen=True)
class ScannerMatch:
    symbol: str
    score: int
    criteria: tuple[ScannerCriterion, ...]
    momentum_percent: Decimal | None = None
    volume_ratio: Decimal | None = None
    resistance_price: Decimal | None = None
    distance_to_resistance_percent: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if not 0 <= self.score <= 100:
            raise ValueError("score must be between 0 and 100")
        if self.volume_ratio is not None and self.volume_ratio < 0:
            raise ValueError("volume_ratio cannot be negative")


@dataclass(frozen=True)
class TechnicalScannerResult:
    scanner_id: str
    matches: tuple[ScannerMatch, ...]
    evaluated_symbols: int
    data_status: str
