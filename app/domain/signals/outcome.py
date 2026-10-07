from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.domain.signals.model import SignalDirection


class SignalOutcome(StrEnum):
    TARGET_HIT = "TARGET_HIT"
    INVALIDATED = "INVALIDATED"


@dataclass(frozen=True)
class SignalOutcomeRecord:
    signal_id: UUID
    symbol: str
    outcome: SignalOutcome
    direction: SignalDirection
    observed_at: datetime
    entry_price: Decimal
    exit_price: Decimal
    realized_return: Decimal
    realized_r: Decimal
    invalidation: Decimal
    target_label: str | None
    strategy_id: str
    strategy_version: str
    data_timestamp: datetime

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.entry_price <= 0 or self.exit_price <= 0:
            raise ValueError("prices must be positive")
        if self.invalidation <= 0:
            raise ValueError("invalidation must be positive")
        if self.realized_r == 0:
            raise ValueError("realized R cannot be zero")
        if not self.strategy_id.strip() or not self.strategy_version.strip():
            raise ValueError("strategy identity is required")
        if self.outcome is SignalOutcome.TARGET_HIT and not self.target_label:
            raise ValueError("target label is required for target hits")
        if self.outcome is SignalOutcome.INVALIDATED and self.target_label is not None:
            raise ValueError("target label must be absent for invalidation")
        if self.data_timestamp > self.observed_at:
            raise ValueError("data timestamp cannot be later than observation")
