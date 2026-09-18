from dataclasses import dataclass
from enum import Enum

from app.application.notifications.deliver_alert import DeliverAlert
from app.application.reporting.get_alert_candidate import GetAlertCandidate
from app.domain.execution import Execution


class AutomaticAlertDeliveryState(Enum):
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


@dataclass(frozen=True)
class AutomaticAlertDeliveryResult:
    state: AutomaticAlertDeliveryState
    attempted_count: int
    delivered_count: int
    skipped_count: int
    failed_count: int
    failure_reasons: dict[str, str]


class AutomaticAlertDelivery:
    def __init__(
        self,
        get_alert_candidate: GetAlertCandidate,
        deliver_alert: DeliverAlert,
        default_channel: str = "telegram",
    ) -> None:
        normalized_channel = default_channel.strip().lower()
        if not normalized_channel:
            raise ValueError("Automatic alert delivery channel cannot be empty")
        self._get_alert_candidate = get_alert_candidate
        self._deliver_alert = deliver_alert
        self._default_channel = normalized_channel

    def execute(self, analysis_execution: Execution) -> AutomaticAlertDeliveryResult:
        attempted = delivered = skipped = failed = 0
        failure_reasons: dict[str, str] = {}

        for symbol in sorted(analysis_execution.successful_stock_ids):
            candidate = self._get_alert_candidate.execute(symbol)
            if candidate is None:
                skipped += 1
                continue

            attempted += 1
            try:
                record = self._deliver_alert.execute(candidate, self._default_channel)
            except Exception as error:
                failed += 1
                failure_reasons[symbol] = str(error) or error.__class__.__name__
                continue

            if record.status.value == "delivered":
                delivered += 1
            else:
                failed += 1
                failure_reasons[symbol] = record.last_error or record.status.value

        if failed == 0:
            state = AutomaticAlertDeliveryState.COMPLETED
        elif delivered == 0:
            state = AutomaticAlertDeliveryState.FAILED
        else:
            state = AutomaticAlertDeliveryState.COMPLETED_WITH_ERRORS

        return AutomaticAlertDeliveryResult(
            state=state,
            attempted_count=attempted,
            delivered_count=delivered,
            skipped_count=skipped,
            failed_count=failed,
            failure_reasons=failure_reasons,
        )
