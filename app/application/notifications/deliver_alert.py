from app.application.notifications.provider import NotificationProvider
from app.domain.reporting.alerts import AlertCandidate
from app.infrastructure.notifications.in_memory_alert_delivery_store import (
    AlertDeliveryRecord,
    AlertDeliveryStatus,
    InMemoryAlertDeliveryStore,
)


class DeliverAlert:
    def __init__(self, store: InMemoryAlertDeliveryStore, provider: NotificationProvider) -> None:
        self._store = store
        self._provider = provider

    def execute(self, candidate: AlertCandidate, channel: str) -> AlertDeliveryRecord:
        if candidate.snapshot_id is None:
            raise ValueError("Alert candidate requires snapshot identity for delivery")
        normalized_channel = channel.strip().lower()
        if not normalized_channel:
            raise ValueError("Delivery channel cannot be empty")

        existing = self._store.get(candidate.stock_id, candidate.snapshot_id, normalized_channel)
        if existing is not None:
            if existing.status in {AlertDeliveryStatus.PENDING, AlertDeliveryStatus.DELIVERED}:
                return existing

        self._store.create_pending(candidate.stock_id, candidate.snapshot_id, normalized_channel)

        try:
            self._provider.send(candidate, normalized_channel)
        except Exception as error:
            reason = str(error) or error.__class__.__name__
            return self._store.mark_failed(
                candidate.stock_id, candidate.snapshot_id, normalized_channel, reason
            )

        return self._store.mark_delivered(
            candidate.stock_id, candidate.snapshot_id, normalized_channel
        )