from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.application.alerts.outbox import AlertOutboxRecord, AlertOutbox
from app.application.alerts.telegram_delivery_store import (
    SignalAlertDeliveryRecord,
    SignalAlertDeliveryStore,
)


class OpportunityNotificationIntegrityError(RuntimeError):
    """A recipient delivery references an event missing from the durable outbox."""


@dataclass(frozen=True)
class UserOpportunityNotification:
    event: AlertOutboxRecord
    delivery: SignalAlertDeliveryRecord


class GetUserOpportunityNotifications:
    """Read only the Telegram opportunity events addressed to one authenticated user."""

    CHANNEL = "telegram"

    def __init__(
        self,
        *,
        deliveries: SignalAlertDeliveryStore,
        outbox: AlertOutbox,
    ) -> None:
        self._deliveries = deliveries
        self._outbox = outbox

    def execute(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
    ) -> tuple[UserOpportunityNotification, ...]:
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")

        delivery_records = self._deliveries.list_for_user(
            user_id,
            self.CHANNEL,
            limit=limit,
        )
        notifications: list[UserOpportunityNotification] = []
        for delivery in delivery_records:
            event = self._outbox.get(delivery.event_id)
            if event is None:
                raise OpportunityNotificationIntegrityError(
                    "recipient delivery references a missing alert event"
                )
            notifications.append(
                UserOpportunityNotification(event=event, delivery=delivery)
            )
        return tuple(notifications)
