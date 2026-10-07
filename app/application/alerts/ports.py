from __future__ import annotations

from typing import Protocol

from app.domain.alerts.model import AlertEvent


class AlertPublisher(Protocol):
    def publish(self, event: AlertEvent) -> None: ...
