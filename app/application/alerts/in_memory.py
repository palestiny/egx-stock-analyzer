from __future__ import annotations

from app.domain.alerts.model import AlertEvent


class InMemoryAlertPublisher:
    def __init__(self) -> None:
        self.events: list[AlertEvent] = []

    def publish(self, event: AlertEvent) -> None:
        self.events.append(event)
