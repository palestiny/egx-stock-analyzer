from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.application.alerts.get_user_opportunity_notifications import (
    OpportunityNotificationIntegrityError,
    UserOpportunityNotification,
)
from app.application.alerts.outbox import AlertOutbox
from app.application.alerts.telegram_delivery_store import SignalAlertDeliveryStore
from app.application.signals.store import SignalHistoryStore, SignalRecord


@dataclass(frozen=True)
class UserOpportunityLifecycleHistory:
    notification: UserOpportunityNotification
    history: tuple[SignalRecord, ...]

    @property
    def current_status(self) -> str:
        return self.history[-1].signal.status.value


class GetUserOpportunityLifecycleHistory:
    """Read lifecycle timelines only for opportunities addressed to this user."""

    CHANNEL = "telegram"

    def __init__(
        self,
        *,
        deliveries: SignalAlertDeliveryStore,
        outbox: AlertOutbox,
        history: SignalHistoryStore,
    ) -> None:
        self._deliveries = deliveries
        self._outbox = outbox
        self._history = history

    def execute(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
    ) -> tuple[UserOpportunityLifecycleHistory, ...]:
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")

        deliveries = self._deliveries.list_for_user(
            user_id,
            self.CHANNEL,
            limit=limit,
        )
        items: dict[UUID, UserOpportunityLifecycleHistory] = {}
        for delivery in deliveries:
            event = self._outbox.get(delivery.event_id)
            if event is None:
                raise OpportunityNotificationIntegrityError(
                    "recipient delivery references a missing alert event"
                )
            if event.event.event_type.value != "SIGNAL_PUBLISHED":
                continue
            signal_id = event.event.signal_id
            if signal_id in items:
                continue
            records = self._history.history(signal_id)
            if not records:
                raise OpportunityNotificationIntegrityError(
                    "published opportunity references missing signal history"
                )
            if not any(record.event in {"PUBLISHED", "PUBLISHED_VERSION"} for record in records):
                raise OpportunityNotificationIntegrityError(
                    "published opportunity has no publication history record"
                )
            items[signal_id] = UserOpportunityLifecycleHistory(
                notification=UserOpportunityNotification(
                    event=event,
                    delivery=delivery,
                ),
                history=records,
            )

        return tuple(
            sorted(
                items.values(),
                key=lambda item: (
                    item.notification.event.event.occurred_at,
                    str(item.notification.event.event.signal_id),
                ),
                reverse=True,
            )[:limit]
        )
