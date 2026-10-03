from dataclasses import dataclass
from enum import Enum


class ScannerCriterion(Enum):
    UPTREND = "uptrend"
    POSITIVE_MOMENTUM = "positive_momentum"
    ABOVE_AVERAGE_VOLUME = "above_average_volume"
    ACTIONABLE_CLASSIFICATION = "actionable_classification"


@dataclass(frozen=True)
class ScannerMatch:
    symbol: str
    score: int
    criteria: tuple[ScannerCriterion, ...]

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if not 0 <= self.score <= 100:
            raise ValueError("score must be between 0 and 100")


@dataclass(frozen=True)
class TechnicalScannerResult:
    scanner_id: str
    matches: tuple[ScannerMatch, ...]
    evaluated_symbols: int
    data_status: str
