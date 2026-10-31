from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class SignalAlertDeliveryStatus(StrEnum):
    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    SENDING = "SENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    SUPPRESSED = "SUPPRESSED"
    DELIVERY_UNKNOWN = "DELIVERY_UNKNOWN"


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
    claim_token: UUID | None = None
    lease_until: datetime | None = None


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

    def claim(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        claim_token: UUID,
        now: datetime,
        lease_until: datetime,
    ) -> bool: ...

    def mark_sending(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        claim_token: UUID,
        now: datetime,
    ) -> bool: ...

    def complete_delivered(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        claim_token: UUID,
        now: datetime,
    ) -> bool: ...

    def complete_failed(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        error: str,
        *,
        claim_token: UUID,
        now: datetime,
    ) -> bool: ...

    def mark_delivery_unknown(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        reason: str,
        *,
        claim_token: UUID,
        now: datetime,
    ) -> bool: ...

    def recover_expired_claims(self, *, now: datetime) -> int: ...

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
