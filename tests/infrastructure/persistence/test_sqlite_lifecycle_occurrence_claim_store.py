from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.signals.occurrence_claims import lifecycle_occurrence_id
from app.domain.alerts.model import AlertEvent, AlertEventType
from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)
from app.infrastructure.persistence.sqlite_lifecycle_occurrence_claim_store import (
    SQLiteLifecycleOccurrenceClaimStore,
    StaleLifecycleOccurrenceClaimError,
)
from app.infrastructure.persistence.sqlite_signal_history_store import SQLiteSignalHistoryStore
from app.infrastructure.persistence.sqlite_signal_lifecycle_unit_of_work import (
    SQLiteSignalLifecycleUnitOfWork,
)
from app.infrastructure.persistence.sqlite_track_record_store import SQLiteTrackRecordStore
from app.infrastructure.notifications.sqlite_alert_outbox import SQLiteAlertOutbox


NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)


def make_signal() -> Signal:
    return Signal(
        symbol="COMI",
        direction=SignalDirection.BUY,
        status=SignalStatus.ACTIVE,
        generated_at=NOW,
        timeframe="DAILY",
        entry_zone=PriceZone(Decimal("99"), Decimal("101")),
        invalidation=Decimal("95"),
        targets=(Target(Decimal("109"), "T1"),),
        confidence=Decimal("80"),
        risk_score=Decimal("20"),
        evidence=(SignalEvidence("trend", "verified trend evidence"),),
        strategy_id="breakout-trend",
        strategy_version="1.0",
        data_timestamp=NOW,
    )


def make_uow(database):
    history = SQLiteSignalHistoryStore(database)
    track_record = SQLiteTrackRecordStore(database)
    outbox = SQLiteAlertOutbox(database)
    return SQLiteSignalLifecycleUnitOfWork(history, track_record, outbox), history


def test_occurrence_identity_is_stable_and_scoped_to_calendar_session_and_opportunity():
    opportunity_id = uuid4()
    first = lifecycle_occurrence_id("egx-2026-v1", date(2026, 11, 12), opportunity_id)

    assert first == lifecycle_occurrence_id("egx-2026-v1", date(2026, 11, 12), opportunity_id)
    assert first != lifecycle_occurrence_id("egx-2026-v2", date(2026, 11, 12), opportunity_id)
    assert first != lifecycle_occurrence_id("egx-2026-v1", date(2026, 11, 13), opportunity_id)
    assert first != lifecycle_occurrence_id("egx-2026-v1", date(2026, 11, 12), uuid4())


def test_only_one_concurrent_worker_can_claim_an_occurrence(tmp_path):
    store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "analysis.db")

    def attempt(owner):
        return store.claim("occurrence-1", owner, now=NOW, lease_seconds=60)

    with ThreadPoolExecutor(max_workers=2) as executor:
        claims = list(executor.map(attempt, ("worker-a", "worker-b")))

    assert sum(claim is not None for claim in claims) == 1
    persisted = store.get("occurrence-1")
    assert persisted is not None
    assert persisted["status"] == "CLAIMED"
    assert persisted["fencing_token"] == 1
    assert persisted["attempt"] == 1


def test_expired_lease_reclaim_increments_fencing_token_and_rejects_old_owner(tmp_path):
    store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "analysis.db")
    first = store.claim("occurrence-2", "worker-a", now=NOW, lease_seconds=30)
    assert first is not None

    second = store.claim(
        "occurrence-2", "worker-b", now=NOW + timedelta(seconds=31), lease_seconds=30
    )

    assert second is not None
    assert second.fencing_token == first.fencing_token + 1
    assert second.attempt == first.attempt + 1
    assert second.owner_id == "worker-b"
    assert store.mark_failed(first, failed_at=NOW + timedelta(seconds=32), reason="stale") is False


def test_failed_occurrence_can_be_retried_with_a_new_fencing_token(tmp_path):
    store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "analysis.db")
    first = store.claim("occurrence-3", "worker-a", now=NOW, lease_seconds=60)
    assert first is not None

    assert store.mark_failed(first, failed_at=NOW + timedelta(seconds=5), reason="provider timeout")

    second = store.claim(
        "occurrence-3", "worker-b", now=NOW + timedelta(seconds=6), lease_seconds=60
    )
    assert second is not None
    assert second.fencing_token == 2
    assert second.attempt == 2


def test_completed_occurrence_cannot_be_claimed_again(tmp_path):
    database = tmp_path / "analysis.db"
    store = SQLiteLifecycleOccurrenceClaimStore(database)
    unit_of_work, history = make_uow(database)
    claim = store.claim("occurrence-4", "worker-a", now=NOW, lease_seconds=60)
    assert claim is not None
    clock_values = iter((NOW + timedelta(seconds=1), NOW + timedelta(seconds=2)))

    unit_of_work.execute_claimed(
        claim,
        lambda transaction: transaction.record_signal(make_signal(), "CREATED", NOW),
        clock=lambda: next(clock_values),
    )

    assert store.get("occurrence-4")["status"] == "COMPLETED"
    assert store.claim(
        "occurrence-4", "worker-b", now=NOW + timedelta(seconds=3), lease_seconds=60
    ) is None
    assert len(history.all_records()) == 1


def test_stale_fencing_token_cannot_write_lifecycle_history(tmp_path):
    database = tmp_path / "analysis.db"
    store = SQLiteLifecycleOccurrenceClaimStore(database)
    unit_of_work, history = make_uow(database)
    old_claim = store.claim("occurrence-5", "worker-a", now=NOW, lease_seconds=10)
    assert old_claim is not None
    new_claim = store.claim(
        "occurrence-5", "worker-b", now=NOW + timedelta(seconds=11), lease_seconds=30
    )
    assert new_claim is not None

    with pytest.raises(StaleLifecycleOccurrenceClaimError):
        unit_of_work.execute_claimed(
            old_claim,
            lambda transaction: transaction.record_signal(make_signal(), "CREATED", NOW),
            clock=lambda: NOW + timedelta(seconds=12),
        )

    assert history.all_records() == ()
    assert store.get("occurrence-5")["owner_id"] == "worker-b"
    assert store.get("occurrence-5")["fencing_token"] == new_claim.fencing_token


def test_lease_expiring_during_lifecycle_transaction_rolls_back_all_writes(tmp_path):
    database = tmp_path / "analysis.db"
    store = SQLiteLifecycleOccurrenceClaimStore(database)
    unit_of_work, history = make_uow(database)
    outbox = SQLiteAlertOutbox(database)
    claim = store.claim("occurrence-6", "worker-a", now=NOW, lease_seconds=10)
    assert claim is not None
    clock_values = iter((NOW + timedelta(seconds=5), NOW + timedelta(seconds=11)))

    def persist_lifecycle_and_alert(transaction):
        created = transaction.record_signal(make_signal(), "CREATED", NOW)
        transaction.publish_alert(
            AlertEvent(
                event_id=uuid4(),
                signal_id=created.signal_id,
                symbol="COMI",
                event_type=AlertEventType.SIGNAL_TRIGGERED,
                occurred_at=NOW,
                message="COMI lifecycle event",
            )
        )

    with pytest.raises(StaleLifecycleOccurrenceClaimError):
        unit_of_work.execute_claimed(
            claim,
            persist_lifecycle_and_alert,
            clock=lambda: next(clock_values),
        )

    assert history.all_records() == ()
    assert outbox.pending() == ()
    assert store.get("occurrence-6")["status"] == "CLAIMED"


def test_claim_store_rejects_naive_time_and_invalid_lease(tmp_path):
    store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "analysis.db")

    with pytest.raises(ValueError, match="timezone-aware"):
        store.claim("occurrence-7", "worker-a", now=datetime(2026, 11, 13), lease_seconds=30)
    with pytest.raises(ValueError, match="positive integer"):
        store.claim("occurrence-7", "worker-a", now=NOW, lease_seconds=0)


def test_claim_survives_store_restart_and_can_be_reclaimed_after_expiry(tmp_path):
    database = tmp_path / "analysis.db"
    first_store = SQLiteLifecycleOccurrenceClaimStore(database)
    first_claim = first_store.claim(
        "occurrence-restart", "worker-before-restart", now=NOW, lease_seconds=10
    )
    assert first_claim is not None

    restarted_store = SQLiteLifecycleOccurrenceClaimStore(database)
    persisted = restarted_store.get("occurrence-restart")
    assert persisted is not None
    assert persisted["owner_id"] == "worker-before-restart"
    assert persisted["fencing_token"] == 1
    assert persisted["attempt"] == 1
    assert persisted["status"] == "CLAIMED"

    assert restarted_store.claim(
        "occurrence-restart",
        "worker-after-restart",
        now=NOW + timedelta(seconds=11),
        lease_seconds=30,
    ) is not None
    recovered = restarted_store.get("occurrence-restart")
    assert recovered is not None
    assert recovered["owner_id"] == "worker-after-restart"
    assert recovered["fencing_token"] == 2
    assert recovered["attempt"] == 2
