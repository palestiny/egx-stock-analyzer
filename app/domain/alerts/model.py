from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class AlertEventType(StrEnum):
    SIGNAL_TRIGGERED = "SIGNAL_TRIGGERED"
    SIGNAL_INVALIDATED = "SIGNAL_INVALIDATED"


@dataclass(frozen=True)
class AlertEvent:
    event_id: UUID
    signal_id: UUID
    symbol: str
    event_type: AlertEventType
    occurred_at: datetime
    message: str

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if not self.message.strip():
            raise ValueError("message is required")
