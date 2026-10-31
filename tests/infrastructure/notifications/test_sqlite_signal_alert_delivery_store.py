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


def test_atomic_claim_allows_only_one_competing_worker(tmp_path) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    store = SQLiteSignalAlertDeliveryStore(tmp_path / "claims.db")
    event_id, user_id = uuid4(), uuid4()
    store.create_pending(event_id, user_id, "telegram", now=NOW)
    barrier = Barrier(2)

    def attempt(token):
        barrier.wait()
        return store.claim(
            event_id, user_id, "telegram",
            claim_token=token,
            now=NOW,
            lease_until=NOW + timedelta(seconds=20),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, (uuid4(), uuid4())))

    assert sorted(outcomes) == [False, True]
    record = store.get(event_id, user_id, "telegram")
    assert record is not None
    assert record.status is SignalAlertDeliveryStatus.CLAIMED
    assert record.claim_token is not None
    assert record.lease_until == NOW + timedelta(seconds=20)


def test_claim_token_fences_stale_worker_completion(tmp_path) -> None:
    store = SQLiteSignalAlertDeliveryStore(tmp_path / "fencing.db")
    event_id, user_id = uuid4(), uuid4()
    first_token, second_token = uuid4(), uuid4()
    store.create_pending(event_id, user_id, "telegram", now=NOW)

    assert store.claim(
        event_id, user_id, "telegram", claim_token=first_token,
        now=NOW, lease_until=NOW + timedelta(seconds=20),
    )
    assert store.mark_sending(
        event_id, user_id, "telegram", claim_token=first_token, now=NOW,
    )
    sending_record = store.get(event_id, user_id, "telegram")
    assert sending_record is not None and sending_record.attempts == 1
    assert store.mark_delivery_unknown(
        event_id, user_id, "telegram", "ambiguous transport result",
        claim_token=first_token, now=NOW + timedelta(seconds=1),
    ) is True

    # DELIVERY_UNKNOWN is intentionally not claimable by another worker.
    assert store.claim(
        event_id, user_id, "telegram", claim_token=second_token,
        now=NOW + timedelta(seconds=2),
        lease_until=NOW + timedelta(seconds=22),
    ) is False
    assert store.complete_delivered(
        event_id, user_id, "telegram", claim_token=first_token,
        now=NOW + timedelta(seconds=3),
    ) is False
    record = store.get(event_id, user_id, "telegram")
    assert record is not None
    assert record.status is SignalAlertDeliveryStatus.DELIVERY_UNKNOWN


def test_expired_pre_send_claim_is_reclaimed_but_expired_send_becomes_unknown(tmp_path) -> None:
    store = SQLiteSignalAlertDeliveryStore(tmp_path / "recovery.db")
    pre_send_event, sending_event, user_id = uuid4(), uuid4(), uuid4()
    old_token, new_token = uuid4(), uuid4()
    store.create_pending(pre_send_event, user_id, "telegram", now=NOW)
    store.create_pending(sending_event, user_id, "telegram", now=NOW)

    assert store.claim(
        pre_send_event, user_id, "telegram", claim_token=old_token,
        now=NOW, lease_until=NOW + timedelta(seconds=5),
    )
    assert store.claim(
        sending_event, user_id, "telegram", claim_token=old_token,
        now=NOW, lease_until=NOW + timedelta(seconds=5),
    )
    assert store.mark_sending(
        sending_event, user_id, "telegram", claim_token=old_token, now=NOW,
    )

    recovered = store.recover_expired_claims(now=NOW + timedelta(seconds=6))

    assert recovered == 2
    pre_send = store.get(pre_send_event, user_id, "telegram")
    sending = store.get(sending_event, user_id, "telegram")
    assert pre_send is not None and pre_send.status is SignalAlertDeliveryStatus.PENDING
    assert sending is not None and sending.status is SignalAlertDeliveryStatus.DELIVERY_UNKNOWN
    assert store.claim(
        pre_send_event, user_id, "telegram", claim_token=new_token,
        now=NOW + timedelta(seconds=6),
        lease_until=NOW + timedelta(seconds=26),
    )
    assert not store.claim(
        sending_event, user_id, "telegram", claim_token=new_token,
        now=NOW + timedelta(seconds=6),
        lease_until=NOW + timedelta(seconds=26),
    )


def test_store_migrates_existing_delivery_table_without_rewriting_rows(tmp_path) -> None:
    import sqlite3

    database = tmp_path / "legacy.db"
    event_id, user_id = uuid4(), uuid4()
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE signal_alert_deliveries (
                event_id TEXT NOT NULL, user_id TEXT NOT NULL, channel TEXT NOT NULL,
                status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_error TEXT NULL,
                PRIMARY KEY(event_id, user_id, channel)
            )
            """
        )
        connection.execute(
            """
            INSERT INTO signal_alert_deliveries
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(event_id), str(user_id), "telegram", "DELIVERED", 1,
                NOW.isoformat(), NOW.isoformat(), None,
            ),
        )

    store = SQLiteSignalAlertDeliveryStore(database)
    record = store.get(event_id, user_id, "telegram")

    assert record is not None
    assert record.status is SignalAlertDeliveryStatus.DELIVERED
    assert record.attempts == 1
    assert record.claim_token is None
    assert record.lease_until is None


def test_expired_claim_token_cannot_complete_even_before_recovery_runs(tmp_path) -> None:
    store = SQLiteSignalAlertDeliveryStore(tmp_path / "expired-token.db")
    event_id, user_id, token = uuid4(), uuid4(), uuid4()
    store.create_pending(event_id, user_id, "telegram", now=NOW)

    assert store.claim(
        event_id, user_id, "telegram", claim_token=token,
        now=NOW, lease_until=NOW + timedelta(seconds=5),
    )
    assert store.mark_sending(
        event_id, user_id, "telegram", claim_token=token, now=NOW,
    )
    assert store.complete_delivered(
        event_id, user_id, "telegram", claim_token=token,
        now=NOW + timedelta(seconds=6),
    ) is False

    assert store.recover_expired_claims(now=NOW + timedelta(seconds=6)) == 1
    record = store.get(event_id, user_id, "telegram")
    assert record is not None
    assert record.status is SignalAlertDeliveryStatus.DELIVERY_UNKNOWN


def test_unfenced_updates_cannot_overwrite_a_live_send_claim(tmp_path) -> None:
    store = SQLiteSignalAlertDeliveryStore(tmp_path / "no-overwrite.db")
    event_id, user_id, token = uuid4(), uuid4(), uuid4()
    store.create_pending(event_id, user_id, "telegram", now=NOW)
    assert store.claim(
        event_id, user_id, "telegram", claim_token=token,
        now=NOW, lease_until=NOW + timedelta(seconds=20),
    )
    assert store.mark_sending(
        event_id, user_id, "telegram", claim_token=token, now=NOW,
    )

    suppressed = store.mark_suppressed(
        event_id, user_id, "telegram", "stale entitlement check",
        now=NOW + timedelta(seconds=1),
    )
    failed = store.mark_failed(
        event_id, user_id, "telegram", "stale failure update",
        now=NOW + timedelta(seconds=1),
    )

    assert suppressed.status is SignalAlertDeliveryStatus.SENDING
    assert failed.status is SignalAlertDeliveryStatus.SENDING
    assert store.complete_delivered(
        event_id, user_id, "telegram", claim_token=token,
        now=NOW + timedelta(seconds=2),
    )


def test_failed_delivery_is_not_claimable_without_retry_policy(tmp_path) -> None:
    store = SQLiteSignalAlertDeliveryStore(tmp_path / "failed-gated.db")
    event_id, user_id = uuid4(), uuid4()
    store.create_pending(event_id, user_id, "telegram", now=NOW)
    failed = store.mark_failed(
        event_id, user_id, "telegram", "definite rejection", now=NOW,
    )
    assert failed.status is SignalAlertDeliveryStatus.FAILED

    assert store.claim(
        event_id, user_id, "telegram", claim_token=uuid4(),
        now=NOW + timedelta(seconds=1),
        lease_until=NOW + timedelta(seconds=21),
    ) is False
    assert store.get(event_id, user_id, "telegram").status is SignalAlertDeliveryStatus.FAILED
