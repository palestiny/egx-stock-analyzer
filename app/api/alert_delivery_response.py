from dataclasses import dataclass
from uuid import UUID

from app.application.notifications.delivery_store import AlertDeliveryRecord


@dataclass(frozen=True)
class AlertDeliveryResponse:
    stock_id: UUID
    snapshot_id: UUID
    channel: str
    status: str
    last_error: str | None

    @classmethod
    def from_record(cls, record: AlertDeliveryRecord) -> "AlertDeliveryResponse":
        return cls(
            stock_id=record.stock_id,
            snapshot_id=record.snapshot_id,
            channel=record.channel,
            status=record.status.value,
            last_error=record.last_error,
        )
