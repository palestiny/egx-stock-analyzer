from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class SignalDirection(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class SignalStatus(StrEnum):
    ACTIVE = "ACTIVE"
    TRIGGERED = "TRIGGERED"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class PriceZone:
    lower: Decimal
    upper: Decimal

    def __post_init__(self) -> None:
        if not self.lower.is_finite() or not self.upper.is_finite():
            raise ValueError("price-zone bounds must be finite")
        if self.lower <= 0 or self.upper <= 0:
            raise ValueError("price-zone bounds must be positive")
        if self.lower > self.upper:
            raise ValueError("price-zone lower bound cannot exceed upper bound")


@dataclass(frozen=True)
class Target:
    price: Decimal
    label: str

    def __post_init__(self) -> None:
        if not self.price.is_finite():
            raise ValueError("target price must be finite")
        if self.price <= 0:
            raise ValueError("target price must be positive")
        if not self.label.strip():
            raise ValueError("target label is required")


@dataclass(frozen=True)
class SignalEvidence:
    kind: str
    description: str
    weight: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        if not self.weight.is_finite():
            raise ValueError("evidence weight must be finite")
        if not self.kind.strip():
            raise ValueError("evidence kind is required")
        if not self.description.strip():
            raise ValueError("evidence description is required")
        if self.weight < 0:
            raise ValueError("evidence weight cannot be negative")


@dataclass(frozen=True)
class Signal:
    symbol: str
    direction: SignalDirection
    status: SignalStatus
    generated_at: datetime
    timeframe: str
    entry_zone: PriceZone
    invalidation: Decimal
    targets: tuple[Target, ...]
    confidence: Decimal
    risk_score: Decimal
    evidence: tuple[SignalEvidence, ...]
    strategy_id: str
    strategy_version: str
    data_timestamp: datetime

    def __post_init__(self) -> None:
        for field_name, timestamp in (
            ("generated_at", self.generated_at),
            ("data_timestamp", self.data_timestamp),
        ):
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")
        if not self.invalidation.is_finite():
            raise ValueError("invalidation must be finite")
        if not self.confidence.is_finite():
            raise ValueError("confidence must be finite")
        if not self.risk_score.is_finite():
            raise ValueError("risk score must be finite")
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if not self.timeframe.strip():
            raise ValueError("timeframe is required")
        if self.invalidation <= 0:
            raise ValueError("invalidation must be positive")
        if not self.strategy_id.strip() or not self.strategy_version.strip():
            raise ValueError("strategy identity is required")
        if not Decimal("0") <= self.confidence <= Decimal("100"):
            raise ValueError("confidence must be between 0 and 100")
        if not Decimal("0") <= self.risk_score <= Decimal("100"):
            raise ValueError("risk score must be between 0 and 100")
        if not self.targets:
            raise ValueError("at least one target is required")
        if not self.evidence:
            raise ValueError("at least one evidence item is required")
        if self.data_timestamp > self.generated_at:
            raise ValueError("data timestamp cannot be later than signal generation")
