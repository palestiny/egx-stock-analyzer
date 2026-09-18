from typing import Protocol

from app.domain.reporting.alerts import AlertCandidate


class NotificationProvider(Protocol):
    def send(self, candidate: AlertCandidate, channel: str) -> None:
        ...