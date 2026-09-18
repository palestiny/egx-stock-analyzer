from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from uuid import UUID


class AlertDeliveryStatus(Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


@dataclass(frozen=True)
class AlertDeliveryRecord:
    stock_id: UUID
    snapshot_id: UUID
    channel: str
    status: AlertDeliveryStatus
    last_error: str | None = None


class AlertDeliveryStore(Protocol):
    def get(self, stock_id: UUID, snapshot_id: UUID, channel: str) -> AlertDeliveryRecord | None:
        ...

    def create_pending(self, stock_id: UUID, snapshot_id: UUID, channel: str) -> AlertDeliveryRecord:
        ...

    def mark_delivered(self, stock_id: UUID, snapshot_id: UUID, channel: str) -> AlertDeliveryRecord:
        ...

    def mark_failed(self, stock_id: UUID, snapshot_id: UUID, channel: str, error: str) -> AlertDeliveryRecord:
        ...