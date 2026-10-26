from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.application.alerts.outbox import AlertOutboxStatus
from app.domain.alerts.model import AlertEvent, AlertEventType
from app.infrastructure.notifications.sqlite_alert_outbox import SQLiteAlertOutbox


NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def make_event(*, message: str = "Signal invalidated") -> AlertEvent:
    return AlertEvent(
        event_id=uuid4(),
        signal_id=uuid4(),
        symbol="COMI",
        event_type=AlertEventType.SIGNAL_INVALIDATED,
        occurred_at=NOW,
        message=message,
    )


def test_sqlite_outbox_persists_event_and_deduplicates_replay(tmp_path) -> None:
    database = tmp_path / "alerts.db"
    store = SQLiteAlertOutbox(database)
    event = make_event()

    store.publish(event)
    store.publish(event)
    reopened = SQLiteAlertOutbox(database)

    records = reopened.pending()
    assert len(records) == 1
    assert records[0].event == event
    assert records[0].status is AlertOutboxStatus.PENDING
    assert records[0].attempts == 0
    assert reopened.get(event.event_id) == records[0]


def test_sqlite_outbox_rejects_same_id_with_different_payload(tmp_path) -> None:
    store = SQLiteAlertOutbox(tmp_path / "alerts.db")
    event = make_event()
    store.publish(event)
    changed = AlertEvent(
        event_id=event.event_id,
        signal_id=event.signal_id,
        symbol=event.symbol,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        message="Changed message with same identity",
    )

    with pytest.raises(ValueError, match="different alert event already recorded"):
        store.publish(changed)


def test_sqlite_outbox_tracks_failure_then_success(tmp_path) -> None:
    store = SQLiteAlertOutbox(tmp_path / "alerts.db")
    event = make_event()
    store.publish(event)

    failed = store.mark_failed(event.event_id, "temporary transport failure")
    assert failed.status is AlertOutboxStatus.FAILED
    assert failed.attempts == 1
    assert failed.last_error == "temporary transport failure"
    assert failed.delivered_at is None

    delivered = store.mark_delivered(
        event.event_id,
        NOW + timedelta(minutes=1),
    )
    assert delivered.status is AlertOutboxStatus.DELIVERED
    assert delivered.attempts == 2
    assert delivered.last_error is None
    assert delivered.delivered_at == NOW + timedelta(minutes=1)
    assert store.pending() == ()


def test_sqlite_outbox_requires_aware_timestamps_and_positive_limit(tmp_path) -> None:
    store = SQLiteAlertOutbox(tmp_path / "alerts.db")
    event = make_event()
    naive_event = AlertEvent(
        event_id=uuid4(),
        signal_id=event.signal_id,
        symbol=event.symbol,
        event_type=event.event_type,
        occurred_at=datetime(2026, 10, 26, 12, 0),
        message=event.message,
    )

    with pytest.raises(ValueError, match="occurred_at must be timezone-aware"):
        store.publish(naive_event)
    with pytest.raises(ValueError, match="limit must be positive"):
        store.pending(0)
    with pytest.raises(ValueError, match="delivered_at must be timezone-aware"):
        store.mark_delivered(event.event_id, datetime(2026, 10, 26, 12, 0))
