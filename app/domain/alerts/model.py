from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class AlertEventType(StrEnum):
    SIGNAL_TRIGGERED = "SIGNAL_TRIGGERED"
    SIGNAL_INVALIDATED = "SIGNAL_INVALIDATED"


@dataclass(frozen=True)
class AlertTargetSnapshot:
    price: Decimal
    label: str

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise ValueError("alert target price must be positive")
        if not self.label.strip():
            raise ValueError("alert target label is required")


@dataclass(frozen=True)
class AlertEvidenceSnapshot:
    kind: str
    description: str

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise ValueError("alert evidence kind is required")
        if not self.description.strip():
            raise ValueError("alert evidence description is required")


@dataclass(frozen=True)
class AlertSignalSnapshot:
    direction: str
    status: str
    timeframe: str
    entry_lower: Decimal
    entry_upper: Decimal
    invalidation: Decimal
    targets: tuple[AlertTargetSnapshot, ...]
    evidence: tuple[AlertEvidenceSnapshot, ...]
    strategy_id: str
    strategy_version: str
    generated_at: datetime
    data_timestamp: datetime

    def __post_init__(self) -> None:
        if not self.direction.strip() or not self.status.strip():
            raise ValueError("alert signal direction and status are required")
        if not self.timeframe.strip():
            raise ValueError("alert signal timeframe is required")
        if self.entry_lower <= 0 or self.entry_upper <= 0:
            raise ValueError("alert signal entry bounds must be positive")
        if self.entry_lower > self.entry_upper:
            raise ValueError("alert signal entry lower bound cannot exceed upper bound")
        if self.invalidation <= 0:
            raise ValueError("alert signal invalidation must be positive")
        if not self.targets:
            raise ValueError("alert signal requires at least one target")
        if not self.evidence:
            raise ValueError("alert signal requires evidence")
        if not self.strategy_id.strip() or not self.strategy_version.strip():
            raise ValueError("alert signal strategy identity is required")
        for name, value in (
            ("generated_at", self.generated_at),
            ("data_timestamp", self.data_timestamp),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True)
class AlertEvent:
    event_id: UUID
    signal_id: UUID
    symbol: str
    event_type: AlertEventType
    occurred_at: datetime
    message: str
    signal_snapshot: AlertSignalSnapshot | None = None

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if not self.message.strip():
            raise ValueError("message is required")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
