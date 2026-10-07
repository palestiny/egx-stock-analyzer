from __future__ import annotations

from app.domain.alerts.model import AlertEvent


class InMemoryAlertPublisher:
    def __init__(self) -> None:
        self.events: list[AlertEvent] = []
        self._by_id: dict[object, AlertEvent] = {}

    def publish(self, event: AlertEvent) -> None:
        existing = self._by_id.get(event.event_id)
        if existing is not None:
            if existing != event:
                raise ValueError("different alert event already published")
            return
        self._by_id[event.event_id] = event
        self.events.append(event)
