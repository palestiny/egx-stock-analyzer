from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.api.user_opportunity_lifecycle_history_response import UserOpportunityLifecycleHistoryResponse
from app.application.alerts.get_user_opportunity_lifecycle_history import (
    GetUserOpportunityLifecycleHistory,
)
from app.domain.alerts.model import AlertEvent, AlertEventType
from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)
from app.infrastructure.notifications.sqlite_alert_outbox import SQLiteAlertOutbox
from app.infrastructure.notifications.sqlite_signal_alert_delivery_store import (
    SQLiteSignalAlertDeliveryStore,
)
from app.infrastructure.persistence.sqlite_signal_history_store import SQLiteSignalHistoryStore


NOW = datetime(2026, 10, 4, 16, tzinfo=timezone.utc)


def make_signal():
    return Signal(
        symbol="COMI",
        direction=SignalDirection.BUY,
        status=SignalStatus.ACTIVE,
        generated_at=datetime(2026, 10, 3, tzinfo=timezone.utc),
        timeframe="DAILY",
        entry_zone=PriceZone(Decimal("99"), Decimal("101")),
        invalidation=Decimal("95"),
        targets=(Target(Decimal("109"), "T1"),),
        confidence=Decimal("80"),
        risk_score=Decimal("20"),
        evidence=(SignalEvidence("trend", "trend evidence"),),
        strategy_id="breakout",
        strategy_version="1.0",
        data_timestamp=datetime(2026, 10, 3, tzinfo=timezone.utc),
    )


def test_user_gets_lifecycle_history_for_their_published_opportunity_only(tmp_path):
    database = tmp_path / "user-lifecycle-history.db"
    history = SQLiteSignalHistoryStore(database)
    outbox = SQLiteAlertOutbox(database)
    deliveries = SQLiteSignalAlertDeliveryStore(database)
    user_id = uuid4()
    other_user_id = uuid4()
    signal = make_signal()
    published = history.record(signal, "PUBLISHED", signal.generated_at)
    revised_signal = replace(
        signal,
        evidence=(SignalEvidence("trend", "revised trend evidence"),),
    )
    revision = history.record_revision(
        revised_signal,
        "PUBLISHED_VERSION",
        NOW + timedelta(minutes=1),
        parent_signal_id=published.signal_id,
        reason="Material evidence change",
    )
    history.record_for_signal(
        published.signal_id,
        replace(signal, status=SignalStatus.TRIGGERED),
        "STATUS_TRIGGERED",
        NOW + timedelta(minutes=2),
    )
    history.record_for_signal(
        revision.signal_id,
        replace(revised_signal, status=SignalStatus.TRIGGERED),
        "STATUS_TRIGGERED",
        NOW + timedelta(minutes=3),
    )

    published_event_id = uuid4()
    outbox.publish(
        AlertEvent(
            event_id=published_event_id,
            signal_id=published.signal_id,
            symbol="COMI",
            event_type=AlertEventType.SIGNAL_PUBLISHED,
            occurred_at=signal.generated_at,
            message="COMI opportunity published",
        )
    )
    deliveries.create_pending(
        published_event_id, user_id, "telegram", now=signal.generated_at
    )

    revision_event_id = uuid4()
    outbox.publish(
        AlertEvent(
            event_id=revision_event_id,
            signal_id=revision.signal_id,
            symbol="COMI",
            event_type=AlertEventType.SIGNAL_PUBLISHED,
            occurred_at=NOW + timedelta(minutes=1),
            message="COMI opportunity revised",
        )
    )
    deliveries.create_pending(
        revision_event_id, user_id, "telegram", now=NOW + timedelta(minutes=1)
    )

    unrelated_event_id = uuid4()
    outbox.publish(
        AlertEvent(
            event_id=unrelated_event_id,
            signal_id=published.signal_id,
            symbol="COMI",
            event_type=AlertEventType.SIGNAL_TRIGGERED,
            occurred_at=NOW,
            message="COMI target reached",
        )
    )
    deliveries.create_pending(unrelated_event_id, other_user_id, "telegram", now=NOW)

    query = GetUserOpportunityLifecycleHistory(
        deliveries=deliveries,
        outbox=outbox,
        history=history,
    )

    user_items = query.execute(user_id)
    other_items = query.execute(other_user_id)

    assert len(user_items) == 2
    original_item = next(
        item for item in user_items
        if item.notification.event.event.signal_id == published.signal_id
    )
    revision_item = next(
        item for item in user_items
        if item.notification.event.event.signal_id == revision.signal_id
    )
    assert original_item.notification.event.event.event_type is AlertEventType.SIGNAL_PUBLISHED
    assert original_item.current_status == "TRIGGERED"
    assert [record.event for record in original_item.history] == [
        "PUBLISHED",
        "STATUS_TRIGGERED",
    ]
    assert revision_item.current_status == "TRIGGERED"
    assert revision_item.revision_link is not None
    assert revision_item.revision_link.parent_signal_id == published.signal_id
    assert other_items == ()
    response = UserOpportunityLifecycleHistoryResponse.from_item(revision_item)
    assert response["current_status"] == "TRIGGERED"
    assert response["revision"]["parent_signal_id"] == str(published.signal_id)
    assert [item["event"] for item in response["lifecycle_history"]] == [
        "PUBLISHED_VERSION",
        "STATUS_TRIGGERED",
    ]


def test_user_lifecycle_history_rejects_missing_signal_history(tmp_path):
    database = tmp_path / "user-lifecycle-integrity.db"
    outbox = SQLiteAlertOutbox(database)
    deliveries = SQLiteSignalAlertDeliveryStore(database)
    user_id = uuid4()
    event_id = uuid4()
    outbox.publish(
        AlertEvent(
            event_id=event_id,
            signal_id=uuid4(),
            symbol="COMI",
            event_type=AlertEventType.SIGNAL_PUBLISHED,
            occurred_at=NOW,
            message="COMI opportunity published",
        )
    )
    deliveries.create_pending(event_id, user_id, "telegram", now=NOW)
    query = GetUserOpportunityLifecycleHistory(
        deliveries=deliveries,
        outbox=outbox,
        history=SQLiteSignalHistoryStore(database),
    )

    import pytest
    from app.application.alerts.get_user_opportunity_notifications import (
        OpportunityNotificationIntegrityError,
    )

    with pytest.raises(OpportunityNotificationIntegrityError, match="missing signal history"):
        query.execute(user_id)
