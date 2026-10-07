from datetime import datetime, timezone
from uuid import uuid4

from app.application.alerts.in_memory import InMemoryAlertPublisher
from app.domain.alerts.model import AlertEvent, AlertEventType


def test_in_memory_alert_publisher_preserves_events():
    publisher = InMemoryAlertPublisher()
    event = AlertEvent(
        event_id=uuid4(),
        signal_id=uuid4(),
        symbol="COMI",
        event_type=AlertEventType.SIGNAL_TRIGGERED,
        occurred_at=datetime(2026, 10, 7, tzinfo=timezone.utc),
        message="COMI signal triggered",
    )
    publisher.publish(event)
    assert publisher.events == [event]
