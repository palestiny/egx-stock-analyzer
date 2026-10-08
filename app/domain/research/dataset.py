from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from enum import StrEnum


class ResearchDataQuality(StrEnum):
    VALID = "VALID"
    MISSING = "MISSING"
    PARTIAL = "PARTIAL"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    STALE = "STALE"


class PriceAdjustment(StrEnum):
    UNADJUSTED = "UNADJUSTED"
    ADJUSTED = "ADJUSTED"


class ExecutionModel(StrEnum):
    NEXT_OPEN = "NEXT_OPEN"


class SameBarAmbiguityPolicy(StrEnum):
    INVALIDATION_FIRST = "INVALIDATION_FIRST"


@dataclass(frozen=True)
class ResearchBar:
    symbol: str
    timeframe: str
    source_timestamp: datetime
    ingestion_timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    provider: str
    dataset_version: str
    quality: ResearchDataQuality = ResearchDataQuality.VALID
    adjustment: PriceAdjustment = PriceAdjustment.UNADJUSTED

    def __post_init__(self) -> None:
        if not self.symbol.strip(): raise ValueError("symbol is required")
        if not self.timeframe.strip(): raise ValueError("timeframe is required")
        if self.source_timestamp.tzinfo is None: raise ValueError("source timestamp must be timezone-aware")
        if self.ingestion_timestamp.tzinfo is None: raise ValueError("ingestion timestamp must be timezone-aware")
        if not self.provider.strip() or not self.dataset_version.strip(): raise ValueError("provider and dataset version are required")
        if min(self.open, self.high, self.low, self.close) <= 0: raise ValueError("OHLC prices must be positive")
        if self.volume < 0: raise ValueError("volume cannot be negative")
        if self.high < max(self.open, self.close, self.low): raise ValueError("high must be at least every OHLC value")
        if self.low > min(self.open, self.close, self.high): raise ValueError("low must be at most every OHLC value")


@dataclass(frozen=True)
class ResearchCostConfig:
    commission_rate: Decimal
    slippage_rate: Decimal

    def __post_init__(self) -> None:
        if self.commission_rate < 0 or self.slippage_rate < 0: raise ValueError("research costs cannot be negative")


@dataclass(frozen=True)
class ResearchRunConfig:
    dataset_version: str
    provider: str
    strategy_id: str
    strategy_version: str
    evaluator_version: str
    execution_model: ExecutionModel = ExecutionModel.NEXT_OPEN
    ambiguity_policy: SameBarAmbiguityPolicy = SameBarAmbiguityPolicy.INVALIDATION_FIRST
    adjustment: PriceAdjustment = PriceAdjustment.UNADJUSTED
    costs: ResearchCostConfig = ResearchCostConfig(commission_rate=Decimal("0"), slippage_rate=Decimal("0"))

    def __post_init__(self) -> None:
        values = (self.dataset_version, self.provider, self.strategy_id, self.strategy_version, self.evaluator_version)
        if any(not value.strip() for value in values): raise ValueError("research run identity fields are required")


def validate_research_bars(bars: tuple[ResearchBar, ...], *, as_of: datetime | None = None) -> None:
    if as_of is not None and as_of.tzinfo is None: raise ValueError("as-of timestamp must be timezone-aware")
    previous: datetime | None = None
    seen: set[datetime] = set()
    for bar in bars:
        if bar.quality is not ResearchDataQuality.VALID: raise ValueError(f"research-ineligible data quality: {bar.quality}")
        if as_of is not None and bar.source_timestamp > as_of: raise ValueError("future data is not eligible for the research point-in-time")
        if bar.source_timestamp in seen: raise ValueError("duplicate source timestamp is not allowed")
        if previous is not None and bar.source_timestamp < previous: raise ValueError("bars must be ordered by source timestamp")
        seen.add(bar.source_timestamp)
        previous = bar.source_timestamp
