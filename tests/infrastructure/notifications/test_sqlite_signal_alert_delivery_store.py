from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.application.alerts.telegram_delivery_store import SignalAlertDeliveryStatus
from app.infrastructure.notifications.sqlite_signal_alert_delivery_store import (
    SQLiteSignalAlertDeliveryStore,
)


NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def test_per_recipient_delivery_is_durable_and_idempotent(tmp_path) -> None:
    database = tmp_path / "deliveries.db"
    store = SQLiteSignalAlertDeliveryStore(database)
    event_id = uuid4()
    user_id = uuid4()

    first = store.create_pending(event_id, user_id, " Telegram ", now=NOW)
    replay = store.create_pending(event_id, user_id, "telegram", now=NOW)
    assert first == replay
    assert first.status is SignalAlertDeliveryStatus.PENDING
    assert first.attempts == 0

    delivered = store.mark_delivered(
        event_id,
        user_id,
        "telegram",
        now=NOW + timedelta(seconds=1),
    )
    reopened = SQLiteSignalAlertDeliveryStore(database)

    assert delivered.status is SignalAlertDeliveryStatus.DELIVERED
    assert delivered.attempts == 1
    assert reopened.get(event_id, user_id, "telegram") == delivered


def test_per_recipient_delivery_failure_can_be_retried(tmp_path) -> None:
    store = SQLiteSignalAlertDeliveryStore(tmp_path / "deliveries.db")
    event_id = uuid4()
    user_id = uuid4()
    store.create_pending(event_id, user_id, "telegram", now=NOW)

    failed = store.mark_failed(
        event_id,
        user_id,
        "telegram",
        "transport error: Timeout",
        now=NOW + timedelta(seconds=1),
    )
    retried = store.mark_delivered(
        event_id,
        user_id,
        "telegram",
        now=NOW + timedelta(seconds=2),
    )

    assert failed.status is SignalAlertDeliveryStatus.FAILED
    assert failed.attempts == 1
    assert retried.status is SignalAlertDeliveryStatus.DELIVERED
    assert retried.attempts == 2
    assert retried.last_error is None


def test_suppressed_delivery_is_terminal_and_records_reason(tmp_path) -> None:
    store = SQLiteSignalAlertDeliveryStore(tmp_path / "deliveries.db")
    event_id = uuid4()
    user_id = uuid4()
    store.create_pending(event_id, user_id, "telegram", now=NOW)

    suppressed = store.mark_suppressed(
        event_id,
        user_id,
        "telegram",
        "entitlement_not_granted",
        now=NOW + timedelta(seconds=1),
    )

    assert suppressed.status is SignalAlertDeliveryStatus.SUPPRESSED
    assert suppressed.attempts == 0
    assert suppressed.last_error == "entitlement_not_granted"


def test_delivery_store_requires_aware_timestamps_and_nonempty_errors(tmp_path) -> None:
    store = SQLiteSignalAlertDeliveryStore(tmp_path / "deliveries.db")
    event_id = uuid4()
    user_id = uuid4()

    with pytest.raises(ValueError, match="timezone-aware"):
        store.create_pending(
            event_id,
            user_id,
            "telegram",
            now=datetime(2026, 10, 26, 12, 0),
        )
    with pytest.raises(ValueError, match="delivery error"):
        store.mark_failed(
            event_id,
            user_id,
            "telegram",
            " ",
            now=NOW,
        )
