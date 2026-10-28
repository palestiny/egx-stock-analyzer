from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.domain.alerts.model import AlertEvent


class AlertOutboxStatus(StrEnum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    SUPPRESSED_NO_RECIPIENTS = "SUPPRESSED_NO_RECIPIENTS"


@dataclass(frozen=True)
class AlertOutboxRecord:
    event: AlertEvent
    status: AlertOutboxStatus
    attempts: int
    created_at: datetime
    delivered_at: datetime | None = None
    last_error: str | None = None


class AlertOutbox(Protocol):
    def publish(self, event: AlertEvent) -> None: ...
    def pending(self, limit: int = 100) -> tuple[AlertOutboxRecord, ...]: ...
    def get(self, event_id: UUID) -> AlertOutboxRecord | None: ...
    def mark_delivered(self, event_id: UUID, delivered_at: datetime) -> AlertOutboxRecord: ...
    def mark_failed(self, event_id: UUID, error: str) -> AlertOutboxRecord: ...
    def mark_suppressed_no_recipients(self, event_id: UUID, reason: str) -> AlertOutboxRecord: ...
