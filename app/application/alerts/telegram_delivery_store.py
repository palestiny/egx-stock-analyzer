from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class SignalAlertDeliveryStatus(StrEnum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    SUPPRESSED = "SUPPRESSED"


@dataclass(frozen=True)
class SignalAlertDeliveryRecord:
    event_id: UUID
    user_id: UUID
    channel: str
    status: SignalAlertDeliveryStatus
    attempts: int
    created_at: datetime
    updated_at: datetime
    last_error: str | None = None


class SignalAlertDeliveryStore(Protocol):
    def get(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
    ) -> SignalAlertDeliveryRecord | None: ...

    def create_pending(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        now: datetime,
    ) -> SignalAlertDeliveryRecord: ...

    def mark_delivered(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        now: datetime,
    ) -> SignalAlertDeliveryRecord: ...

    def mark_failed(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        error: str,
        *,
        now: datetime,
    ) -> SignalAlertDeliveryRecord: ...

    def mark_suppressed(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        reason: str,
        *,
        now: datetime,
    ) -> SignalAlertDeliveryRecord: ...
