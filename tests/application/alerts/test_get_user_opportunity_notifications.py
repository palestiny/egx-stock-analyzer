from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.application.alerts.get_user_opportunity_notifications import (
    GetUserOpportunityNotifications,
    OpportunityNotificationIntegrityError,
)
from app.domain.alerts.model import AlertEvent, AlertEventType
from app.infrastructure.notifications.sqlite_alert_outbox import SQLiteAlertOutbox
from app.infrastructure.notifications.sqlite_signal_alert_delivery_store import (
    SQLiteSignalAlertDeliveryStore,
)


NOW = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)


def make_event(event_id, signal_id):
    return AlertEvent(
        event_id=event_id,
        signal_id=signal_id,
        symbol="EGAL",
        event_type=AlertEventType.SIGNAL_PUBLISHED,
        occurred_at=NOW,
        message="EGAL opportunity published",
    )


def test_query_returns_only_the_authenticated_users_delivery_events(tmp_path):
    database = tmp_path / "notifications.db"
    outbox = SQLiteAlertOutbox(database)
    deliveries = SQLiteSignalAlertDeliveryStore(database)
    user_id, other_user_id = uuid4(), uuid4()
    event_id, other_event_id = uuid4(), uuid4()
    outbox.publish(make_event(event_id, uuid4()))
    outbox.publish(make_event(other_event_id, uuid4()))
    deliveries.create_pending(event_id, user_id, "telegram", now=NOW)
    deliveries.create_pending(other_event_id, other_user_id, "telegram", now=NOW)

    result = GetUserOpportunityNotifications(
        deliveries=deliveries,
        outbox=outbox,
    ).execute(user_id)

    assert len(result) == 1
    assert result[0].event.event.event_id == event_id
    assert result[0].delivery.user_id == user_id


def test_query_rejects_delivery_rows_with_missing_outbox_events(tmp_path):
    database = tmp_path / "orphan-notifications.db"
    outbox = SQLiteAlertOutbox(database)
    deliveries = SQLiteSignalAlertDeliveryStore(database)
    user_id = uuid4()
    deliveries.create_pending(uuid4(), user_id, "telegram", now=NOW)

    query = GetUserOpportunityNotifications(
        deliveries=deliveries,
        outbox=outbox,
    )
    with pytest.raises(OpportunityNotificationIntegrityError):
        query.execute(user_id)


def test_query_validates_page_size(tmp_path):
    database = tmp_path / "limit-notifications.db"
    query = GetUserOpportunityNotifications(
        deliveries=SQLiteSignalAlertDeliveryStore(database),
        outbox=SQLiteAlertOutbox(database),
    )

    with pytest.raises(ValueError, match="between 1 and 200"):
        query.execute(uuid4(), limit=0)
