from __future__ import annotations

from app.application.alerts.get_user_opportunity_lifecycle_history import (
    UserOpportunityLifecycleHistory,
)
from app.api.user_opportunity_notification_response import (
    UserOpportunityNotificationResponse,
)


class UserOpportunityLifecycleHistoryResponse:
    @staticmethod
    def from_item(item: UserOpportunityLifecycleHistory) -> dict[str, object]:
        return {
            **UserOpportunityNotificationResponse.from_notification(item.notification),
            "current_status": item.current_status,
            "lifecycle_history": [
                {
                    "event": record.event,
                    "recorded_at": record.recorded_at.isoformat(),
                    "status": record.signal.status.value,
                    "signal": {
                        "direction": record.signal.direction.value,
                        "timeframe": record.signal.timeframe,
                        "entry_lower": str(record.signal.entry_zone.lower),
                        "entry_upper": str(record.signal.entry_zone.upper),
                        "invalidation": str(record.signal.invalidation),
                        "targets": [
                            {"price": str(target.price), "label": target.label}
                            for target in record.signal.targets
                        ],
                        "evidence": [
                            {
                                "kind": evidence.kind,
                                "description": evidence.description,
                                "weight": str(evidence.weight),
                            }
                            for evidence in record.signal.evidence
                        ],
                        "strategy_id": record.signal.strategy_id,
                        "strategy_version": record.signal.strategy_version,
                        "generated_at": record.signal.generated_at.isoformat(),
                        "data_timestamp": record.signal.data_timestamp.isoformat(),
                    },
                }
                for record in item.history
            ],
        }
