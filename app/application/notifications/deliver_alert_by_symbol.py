from app.application.notifications.deliver_alert import DeliverAlert
from app.application.notifications.delivery_store import AlertDeliveryRecord
from app.application.reporting.get_alert_candidate import GetAlertCandidate


class AlertCandidateNotFoundError(ValueError):
    """Raised when no deliverable alert candidate exists for a symbol."""


class DeliverAlertBySymbol:
    def __init__(
        self,
        get_alert_candidate: GetAlertCandidate,
        deliver_alert: DeliverAlert,
    ) -> None:
        self._get_alert_candidate = get_alert_candidate
        self._deliver_alert = deliver_alert

    def execute(self, symbol: str, channel: str) -> AlertDeliveryRecord:
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("Alert symbol cannot be empty")

        candidate = self._get_alert_candidate.execute(normalized_symbol)
        if candidate is None:
            raise AlertCandidateNotFoundError(
                f"Alert candidate not found for {normalized_symbol}"
            )

        return self._deliver_alert.execute(candidate, channel)
