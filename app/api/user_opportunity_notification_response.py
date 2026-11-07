from __future__ import annotations

from app.application.alerts.get_user_opportunity_notifications import (
    UserOpportunityNotification,
)


class UserOpportunityNotificationResponse:
    @staticmethod
    def from_notification(
        item: UserOpportunityNotification,
    ) -> dict[str, object]:
        event = item.event.event
        delivery = item.delivery
        snapshot = event.signal_snapshot
        return {
            "event_id": str(event.event_id),
            "signal_id": str(event.signal_id),
            "symbol": event.symbol,
            "event_type": event.event_type.value,
            "occurred_at": event.occurred_at.isoformat(),
            "message": event.message,
            "signal": (
                {
                    "direction": snapshot.direction,
                    "status": snapshot.status,
                    "timeframe": snapshot.timeframe,
                    "entry_lower": str(snapshot.entry_lower),
                    "entry_upper": str(snapshot.entry_upper),
                    "invalidation": str(snapshot.invalidation),
                    "targets": [
                        {"price": str(target.price), "label": target.label}
                        for target in snapshot.targets
                    ],
                    "evidence": [
                        {"kind": evidence.kind, "description": evidence.description}
                        for evidence in snapshot.evidence
                    ],
                    "strategy_id": snapshot.strategy_id,
                    "strategy_version": snapshot.strategy_version,
                    "generated_at": snapshot.generated_at.isoformat(),
                    "data_timestamp": snapshot.data_timestamp.isoformat(),
                }
                if snapshot is not None
                else None
            ),
            "delivery": {
                "channel": delivery.channel,
                "status": delivery.status.value,
                "attempts": delivery.attempts,
                "created_at": delivery.created_at.isoformat(),
                "updated_at": delivery.updated_at.isoformat(),
                "next_attempt_at": (
                    delivery.next_attempt_at.isoformat()
                    if delivery.next_attempt_at is not None
                    else None
                ),
            },
        }
