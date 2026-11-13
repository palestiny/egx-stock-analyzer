from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.signals.occurrence_claims import LifecycleRetryPolicy, lifecycle_occurrence_id
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
TEST_RETRY_POLICY = LifecycleRetryPolicy(max_attempts=3, retry_delays_seconds=(0, 0))


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
    claim_store = SQLiteLifecycleOccurrenceClaimStore(database)
    return SQLiteSignalLifecycleUnitOfWork(
        history, track_record, outbox, occurrence_claim_store=claim_store
    ), history


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
        return store.claim("occurrence-1", owner, now=NOW, lease_seconds=60, retry_policy=TEST_RETRY_POLICY)

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
    first = store.claim("occurrence-2", "worker-a", now=NOW, lease_seconds=30, retry_policy=TEST_RETRY_POLICY)
    assert first is not None

    second = store.claim(
        "occurrence-2", "worker-b", now=NOW + timedelta(seconds=31), lease_seconds=30
    , retry_policy=TEST_RETRY_POLICY)

    assert second is not None
    assert second.fencing_token == first.fencing_token + 1
    assert second.attempt == first.attempt + 1
    assert second.owner_id == "worker-b"
    assert store.mark_failed(first, failed_at=NOW + timedelta(seconds=32), reason="stale") is False


def test_failed_occurrence_can_be_retried_with_a_new_fencing_token(tmp_path):
    store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "analysis.db")
    first = store.claim("occurrence-3", "worker-a", now=NOW, lease_seconds=60, retry_policy=TEST_RETRY_POLICY)
    assert first is not None

    assert store.mark_failed(first, failed_at=NOW + timedelta(seconds=5), reason="provider timeout")

    second = store.claim(
        "occurrence-3", "worker-b", now=NOW + timedelta(seconds=6), lease_seconds=60
    , retry_policy=TEST_RETRY_POLICY)
    assert second is not None
    assert second.fencing_token == 2
    assert second.attempt == 2


def test_completed_occurrence_cannot_be_claimed_again(tmp_path):
    database = tmp_path / "analysis.db"
    store = SQLiteLifecycleOccurrenceClaimStore(database)
    unit_of_work, history = make_uow(database)
    claim = store.claim("occurrence-4", "worker-a", now=NOW, lease_seconds=60, retry_policy=TEST_RETRY_POLICY)
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
    , retry_policy=TEST_RETRY_POLICY) is None
    assert len(history.all_records()) == 1


def test_stale_fencing_token_cannot_write_lifecycle_history(tmp_path):
    database = tmp_path / "analysis.db"
    store = SQLiteLifecycleOccurrenceClaimStore(database)
    unit_of_work, history = make_uow(database)
    old_claim = store.claim("occurrence-5", "worker-a", now=NOW, lease_seconds=10, retry_policy=TEST_RETRY_POLICY)
    assert old_claim is not None
    new_claim = store.claim(
        "occurrence-5", "worker-b", now=NOW + timedelta(seconds=11), lease_seconds=30
    , retry_policy=TEST_RETRY_POLICY)
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
    claim = store.claim("occurrence-6", "worker-a", now=NOW, lease_seconds=10, retry_policy=TEST_RETRY_POLICY)
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
        store.claim("occurrence-7", "worker-a", now=datetime(2026, 11, 13), lease_seconds=30, retry_policy=TEST_RETRY_POLICY)
    with pytest.raises(ValueError, match="positive integer"):
        store.claim("occurrence-7", "worker-a", now=NOW, lease_seconds=0, retry_policy=TEST_RETRY_POLICY)


def test_claim_survives_store_restart_and_can_be_reclaimed_after_expiry(tmp_path):
    database = tmp_path / "analysis.db"
    first_store = SQLiteLifecycleOccurrenceClaimStore(database)
    first_claim = first_store.claim(
        "occurrence-restart", "worker-before-restart", now=NOW, lease_seconds=10
    , retry_policy=TEST_RETRY_POLICY)
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
    , retry_policy=TEST_RETRY_POLICY) is not None
    recovered = restarted_store.get("occurrence-restart")
    assert recovered is not None
    assert recovered["owner_id"] == "worker-after-restart"
    assert recovered["fencing_token"] == 2
    assert recovered["attempt"] == 2


def test_current_owner_can_renew_live_claim_without_changing_identity_or_attempt(tmp_path):
    database = tmp_path / "analysis.db"
    store = SQLiteLifecycleOccurrenceClaimStore(database)
    claim = store.claim("occurrence-renew", "worker-a", now=NOW, lease_seconds=10, retry_policy=TEST_RETRY_POLICY)
    assert claim is not None

    renewed = store.renew(
        claim, now=NOW + timedelta(seconds=5), lease_seconds=40
    )

    assert renewed is not None
    assert renewed.occurrence_id == claim.occurrence_id
    assert renewed.owner_id == claim.owner_id
    assert renewed.fencing_token == claim.fencing_token
    assert renewed.attempt == claim.attempt
    assert renewed.lease_until == NOW + timedelta(seconds=45)
    persisted = store.get("occurrence-renew")
    assert persisted is not None
    assert persisted["lease_until"] == renewed.lease_until
    assert persisted["claimed_at"] == NOW


def test_expired_claim_cannot_be_renewed_including_at_exact_expiry(tmp_path):
    store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "analysis.db")
    claim = store.claim("occurrence-renew-expired", "worker-a", now=NOW, lease_seconds=10, retry_policy=TEST_RETRY_POLICY)
    assert claim is not None

    assert store.renew(
        claim, now=NOW + timedelta(seconds=10), lease_seconds=30
    ) is None
    assert store.renew(
        claim, now=NOW + timedelta(seconds=11), lease_seconds=30
    ) is None


def test_old_owner_and_fencing_token_cannot_renew_after_reclaim(tmp_path):
    store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "analysis.db")
    old_claim = store.claim("occurrence-renew-fenced", "worker-a", now=NOW, lease_seconds=10, retry_policy=TEST_RETRY_POLICY)
    assert old_claim is not None
    current_claim = store.claim(
        "occurrence-renew-fenced",
        "worker-b",
        now=NOW + timedelta(seconds=11),
        lease_seconds=30,
    , retry_policy=TEST_RETRY_POLICY)
    assert current_claim is not None

    assert store.renew(
        old_claim, now=NOW + timedelta(seconds=12), lease_seconds=60
    ) is None
    wrong_token = type(current_claim)(
        occurrence_id=current_claim.occurrence_id,
        owner_id=current_claim.owner_id,
        fencing_token=current_claim.fencing_token + 1,
        attempt=current_claim.attempt,
        lease_until=current_claim.lease_until,
    )
    assert store.renew(
        wrong_token, now=NOW + timedelta(seconds=12), lease_seconds=60
    ) is None
    assert store.get("occurrence-renew-fenced")["owner_id"] == "worker-b"
    assert store.get("occurrence-renew-fenced")["fencing_token"] == current_claim.fencing_token


def test_renewed_lease_survives_store_reopen(tmp_path):
    database = tmp_path / "analysis.db"
    store = SQLiteLifecycleOccurrenceClaimStore(database)
    claim = store.claim("occurrence-renew-restart", "worker-a", now=NOW, lease_seconds=10, retry_policy=TEST_RETRY_POLICY)
    assert claim is not None
    renewed = store.renew(
        claim, now=NOW + timedelta(seconds=5), lease_seconds=50
    )
    assert renewed is not None

    reopened = SQLiteLifecycleOccurrenceClaimStore(database)
    persisted = reopened.get("occurrence-renew-restart")
    assert persisted is not None
    assert persisted["lease_until"] == NOW + timedelta(seconds=55)
    assert persisted["claimed_at"] == NOW
    assert persisted["fencing_token"] == claim.fencing_token
    assert persisted["attempt"] == claim.attempt


def test_renew_rejects_naive_time_and_invalid_lease(tmp_path):
    store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "analysis.db")
    claim = store.claim("occurrence-renew-invalid", "worker-a", now=NOW, lease_seconds=10, retry_policy=TEST_RETRY_POLICY)
    assert claim is not None

    with pytest.raises(ValueError, match="timezone-aware"):
        store.renew(claim, now=datetime(2026, 11, 13), lease_seconds=10)
    with pytest.raises(ValueError, match="positive integer"):
        store.renew(claim, now=NOW + timedelta(seconds=1), lease_seconds=0)


def test_unit_of_work_rejects_claim_store_on_a_different_database(tmp_path):
    database = tmp_path / "lifecycle.db"
    history = SQLiteSignalHistoryStore(database)
    track_record = SQLiteTrackRecordStore(database)
    outbox = SQLiteAlertOutbox(database)
    wrong_claim_store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "claims.db")

    with pytest.raises(ValueError, match="share the lifecycle SQLite database"):
        SQLiteSignalLifecycleUnitOfWork(
            history, track_record, outbox, occurrence_claim_store=wrong_claim_store
        )


def test_execute_claimed_requires_explicit_database_bound_claim_store(tmp_path):
    database = tmp_path / "lifecycle.db"
    history = SQLiteSignalHistoryStore(database)
    track_record = SQLiteTrackRecordStore(database)
    outbox = SQLiteAlertOutbox(database)
    unit_of_work = SQLiteSignalLifecycleUnitOfWork(history, track_record, outbox)

    claim = SQLiteLifecycleOccurrenceClaimStore(database).claim(
        "occurrence-no-bound-store", "worker-a", now=NOW, lease_seconds=30
    , retry_policy=TEST_RETRY_POLICY)
    assert claim is not None

    with pytest.raises(RuntimeError, match="requires an occurrence claim store"):
        unit_of_work.execute_claimed(
            claim,
            lambda transaction: transaction.record_signal(make_signal(), "CREATED", NOW),
            clock=lambda: NOW + timedelta(seconds=1),
        )

def test_retry_policy_validates_attempt_budget_and_delays():
    with pytest.raises(ValueError, match="positive integer"):
        LifecycleRetryPolicy(max_attempts=0, retry_delays_seconds=())
    with pytest.raises(ValueError, match="max_attempts - 1"):
        LifecycleRetryPolicy(max_attempts=3, retry_delays_seconds=(1,))
    with pytest.raises(ValueError, match="non-negative integers"):
        LifecycleRetryPolicy(max_attempts=2, retry_delays_seconds=(-1,))


def test_failed_retry_waits_for_persisted_eligibility_without_consuming_attempt(tmp_path):
    store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "analysis.db")
    policy = LifecycleRetryPolicy(max_attempts=3, retry_delays_seconds=(30, 60))
    first = store.claim("bounded-delay", "worker-a", now=NOW, lease_seconds=60, retry_policy=policy)
    assert first is not None
    failed_at = NOW + timedelta(seconds=5)
    assert store.mark_failed(first, failed_at=failed_at, reason="temporary failure")

    deferred = store.claim(
        "bounded-delay", "worker-b", now=NOW + timedelta(seconds=34),
        lease_seconds=60, retry_policy=policy,
    )
    assert deferred is None
    persisted = store.get("bounded-delay")
    assert persisted["status"] == "FAILED"
    assert persisted["attempt"] == 1
    assert persisted["fencing_token"] == 1
    assert persisted["next_attempt_at"] == NOW + timedelta(seconds=35)

    second = store.claim(
        "bounded-delay", "worker-b", now=NOW + timedelta(seconds=35),
        lease_seconds=60, retry_policy=policy,
    )
    assert second is not None
    assert second.attempt == 2
    assert second.fencing_token == 2


def test_retry_policy_is_immutable_for_an_occurrence(tmp_path):
    store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "analysis.db")
    original = LifecycleRetryPolicy(max_attempts=3, retry_delays_seconds=(0, 0))
    changed = LifecycleRetryPolicy(max_attempts=4, retry_delays_seconds=(0, 0, 0))
    assert store.claim(
        "immutable-policy", "worker-a", now=NOW, lease_seconds=60, retry_policy=original
    ) is not None
    with pytest.raises(ValueError, match="cannot change"):
        store.claim(
            "immutable-policy", "worker-b", now=NOW + timedelta(seconds=1),
            lease_seconds=60, retry_policy=changed,
        )


def test_final_failed_attempt_becomes_terminal_exhausted(tmp_path):
    store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "analysis.db")
    policy = LifecycleRetryPolicy(max_attempts=1, retry_delays_seconds=())
    claim = store.claim(
        "final-failure", "worker-a", now=NOW, lease_seconds=60, retry_policy=policy
    )
    assert claim is not None
    assert store.mark_failed(claim, failed_at=NOW + timedelta(seconds=1), reason="fatal")
    persisted = store.get("final-failure")
    assert persisted["status"] == "EXHAUSTED"
    assert persisted["exhausted_at"] == NOW + timedelta(seconds=1)
    assert store.claim(
        "final-failure", "worker-b", now=NOW + timedelta(seconds=2),
        lease_seconds=60, retry_policy=policy,
    ) is None


def test_expired_lease_uses_lease_boundary_and_persisted_backoff(tmp_path):
    store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "analysis.db")
    policy = LifecycleRetryPolicy(max_attempts=3, retry_delays_seconds=(30, 60))
    first = store.claim(
        "expired-backoff", "worker-a", now=NOW, lease_seconds=10, retry_policy=policy
    )
    assert first is not None

    assert store.claim(
        "expired-backoff", "worker-b", now=NOW + timedelta(seconds=39),
        lease_seconds=60, retry_policy=policy,
    ) is None
    persisted = store.get("expired-backoff")
    assert persisted["status"] == "FAILED"
    assert persisted["attempt"] == 1
    assert persisted["next_attempt_at"] == NOW + timedelta(seconds=40)

    second = store.claim(
        "expired-backoff", "worker-b", now=NOW + timedelta(seconds=40),
        lease_seconds=60, retry_policy=policy,
    )
    assert second is not None
    assert second.attempt == 2
    assert second.fencing_token == 2


def test_expired_final_lease_becomes_exhausted(tmp_path):
    store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "analysis.db")
    policy = LifecycleRetryPolicy(max_attempts=1, retry_delays_seconds=())
    claim = store.claim(
        "expired-final", "worker-a", now=NOW, lease_seconds=10, retry_policy=policy
    )
    assert claim is not None

    assert store.claim(
        "expired-final", "worker-b", now=NOW + timedelta(seconds=11),
        lease_seconds=60, retry_policy=policy,
    ) is None
    persisted = store.get("expired-final")
    assert persisted["status"] == "EXHAUSTED"
    assert persisted["attempt"] == 1


def test_concurrent_eligible_retries_only_issue_one_new_fence(tmp_path):
    store = SQLiteLifecycleOccurrenceClaimStore(tmp_path / "analysis.db")
    policy = LifecycleRetryPolicy(max_attempts=3, retry_delays_seconds=(0, 0))
    first = store.claim(
        "concurrent-retry", "worker-a", now=NOW, lease_seconds=60, retry_policy=policy
    )
    assert first is not None
    assert store.mark_failed(first, failed_at=NOW + timedelta(seconds=1), reason="retry")

    def attempt(owner):
        return store.claim(
            "concurrent-retry", owner, now=NOW + timedelta(seconds=2),
            lease_seconds=60, retry_policy=policy,
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        claims = list(executor.map(attempt, ("b", "c", "d", "e")))
    winners = [claim for claim in claims if claim is not None]
    assert len(winners) == 1
    assert winners[0].attempt == 2
    assert winners[0].fencing_token == 2


def test_legacy_rows_are_blocked_until_audited_operator_recovery(tmp_path):
    database = tmp_path / "legacy.db"
    connection = __import__("sqlite3").connect(database)
    connection.execute(
        """
        CREATE TABLE lifecycle_occurrence_claims (
            occurrence_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            fencing_token INTEGER NOT NULL CHECK(fencing_token > 0),
            attempt INTEGER NOT NULL CHECK(attempt > 0),
            status TEXT NOT NULL CHECK(status IN ('CLAIMED', 'FAILED', 'COMPLETED')),
            lease_until TEXT NULL,
            claimed_at TEXT NOT NULL,
            completed_at TEXT NULL,
            last_error TEXT NULL,
            CHECK(
                (status = 'CLAIMED' AND lease_until IS NOT NULL AND completed_at IS NULL)
                OR (status = 'FAILED' AND lease_until IS NULL AND completed_at IS NULL)
                OR (status = 'COMPLETED' AND lease_until IS NULL AND completed_at IS NOT NULL)
            )
        )
        """
    )
    connection.execute(
        """
        INSERT INTO lifecycle_occurrence_claims(
            occurrence_id, owner_id, fencing_token, attempt, status,
            lease_until, claimed_at, completed_at, last_error
        ) VALUES ('legacy-occurrence', 'old-worker', 4, 2, 'FAILED', NULL, ?, NULL, 'old failure')
        """,
        (NOW.isoformat(),),
    )
    connection.commit()
    connection.close()

    store = SQLiteLifecycleOccurrenceClaimStore(database)
    legacy = store.get("legacy-occurrence")
    assert legacy["status"] == "LEGACY_BLOCKED"
    assert legacy["retry_policy"] is None
    assert legacy["attempt"] == 2
    assert store.claim(
        "legacy-occurrence", "worker-new", now=NOW + timedelta(seconds=1),
        lease_seconds=30,
        retry_policy=LifecycleRetryPolicy(max_attempts=2, retry_delays_seconds=(0,)),
    ) is None

    policy = LifecycleRetryPolicy(max_attempts=2, retry_delays_seconds=(0,))
    assert store.recover(
        "legacy-occurrence", retry_policy=policy, actor_id="operator-1",
        reason="approved recovery", recovered_at=NOW + timedelta(seconds=2),
    )
    recovered = store.get("legacy-occurrence")
    assert recovered["status"] == "FAILED"
    assert recovered["attempt"] == 0
    assert recovered["recovery_generation"] == 1
    claim = store.claim(
        "legacy-occurrence", "worker-new", now=NOW + timedelta(seconds=2),
        lease_seconds=30, retry_policy=policy,
    )
    assert claim is not None
    assert claim.attempt == 1
    assert claim.fencing_token == 5
    audit = __import__("sqlite3").connect(database)
    recovery = audit.execute(
        "SELECT actor_id, reason, previous_status, recovery_generation "
        "FROM lifecycle_occurrence_claim_recoveries"
    ).fetchone()
    audit.close()
    assert recovery == ("operator-1", "approved recovery", "LEGACY_BLOCKED", 1)
