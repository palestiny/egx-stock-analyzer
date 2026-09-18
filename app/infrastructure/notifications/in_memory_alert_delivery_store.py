from dataclasses import dataclass
from enum import Enum
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


class InMemoryAlertDeliveryStore:
    def __init__(self) -> None:
        self._records: dict[tuple[UUID, UUID, str], AlertDeliveryRecord] = {}

    def get(self, stock_id: UUID, snapshot_id: UUID, channel: str) -> AlertDeliveryRecord | None:
        return self._records.get((stock_id, snapshot_id, channel))

    def create_pending(self, stock_id: UUID, snapshot_id: UUID, channel: str) -> AlertDeliveryRecord:
        key = (stock_id, snapshot_id, channel)
        existing = self._records.get(key)
        if existing is not None:
            return existing
        record = AlertDeliveryRecord(stock_id, snapshot_id, channel, AlertDeliveryStatus.PENDING)
        self._records[key] = record
        return record

    def mark_delivered(self, stock_id: UUID, snapshot_id: UUID, channel: str) -> AlertDeliveryRecord:
        key = (stock_id, snapshot_id, channel)
        current = self._records[key]
        record = AlertDeliveryRecord(current.stock_id, current.snapshot_id, current.channel, AlertDeliveryStatus.DELIVERED)
        self._records[key] = record
        return record

    def mark_failed(self, stock_id: UUID, snapshot_id: UUID, channel: str, error: str) -> AlertDeliveryRecord:
        key = (stock_id, snapshot_id, channel)
        current = self._records[key]
        record = AlertDeliveryRecord(current.stock_id, current.snapshot_id, current.channel, AlertDeliveryStatus.FAILED, error)
        self._records[key] = record
        return record