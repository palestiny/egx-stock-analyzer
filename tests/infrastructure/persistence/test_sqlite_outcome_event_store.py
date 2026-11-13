import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.signals.model import SignalDirection
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord
from app.domain.signals.outcome_event import OutcomeCorrectionDecision, OutcomeEventKind
from app.infrastructure.persistence.sqlite_outcome_event_store import SQLiteOutcomeEventStore


def make_outcome(signal_id=None, *, exit_price="95"):
    now = datetime(2026, 10, 10, 10, tzinfo=timezone.utc)
    return SignalOutcomeRecord(
        signal_id=signal_id or uuid4(),
        symbol="EGAL",
        outcome=SignalOutcome.INVALIDATED,
        direction=SignalDirection.BUY,
        observed_at=now,
        entry_price=Decimal("100"),
        exit_price=Decimal(exit_price),
        realized_return=Decimal("-0.05"),
        realized_r=Decimal("-1"),
        invalidation=Decimal("95"),
        target_label=None,
        strategy_id="trend",
        strategy_version="1",
        data_timestamp=now,
    )


def test_sqlite_outcome_event_store_survives_restart_and_reconstructs_knowledge_time(tmp_path):
    now = [datetime(2026, 10, 15, 12, tzinfo=timezone.utc)]
    path = tmp_path / "outcomes.db"
    store = SQLiteOutcomeEventStore(path, clock=lambda: now[0])
    outcome = make_outcome()
    event = store.record_initial(
        outcome, actor_id="operator-1", idempotency_key="initial-1"
    )

    reopened = SQLiteOutcomeEventStore(path, clock=lambda: now[0])
    assert reopened.outcome_as_of(
        outcome.signal_id, cutoff=now[0] - timedelta(seconds=1)
    ) is None
    assert reopened.outcome_as_of(outcome.signal_id, cutoff=now[0]) == event
    assert reopened.events_for(outcome.signal_id) == (event,)


def test_sqlite_outcome_event_store_persists_reviewed_corrections(tmp_path):
    now = [datetime(2026, 10, 15, 12, tzinfo=timezone.utc)]
    path = tmp_path / "outcomes.db"
    store = SQLiteOutcomeEventStore(path, clock=lambda: now[0])
    original = store.record_initial(
        make_outcome(), actor_id="author-1", idempotency_key="initial-1"
    )
    correction = store.submit_correction(
        make_outcome(original.signal_id, exit_price="96"),
        supersedes_event_id=original.event_id,
        actor_id="author-2",
        idempotency_key="correction-1",
    )
    now[0] += timedelta(hours=1)
    store.review_correction(
        correction.event_id,
        reviewer_id="reviewer-1",
        decision=OutcomeCorrectionDecision.ACCEPTED,
        idempotency_key="review-1",
    )

    reopened = SQLiteOutcomeEventStore(path, clock=lambda: now[0])
    assert reopened.outcome_as_of(original.signal_id, cutoff=now[0]) == correction
    assert [event.kind for event in reopened.events_for(original.signal_id)] == [
        OutcomeEventKind.OUTCOME_RECORDED,
        OutcomeEventKind.CORRECTION_SUBMITTED,
        OutcomeEventKind.CORRECTION_REVIEWED,
    ]


def test_sqlite_outcome_event_rows_are_append_only(tmp_path):
    path = tmp_path / "outcomes.db"
    store = SQLiteOutcomeEventStore(path)
    outcome = make_outcome()
    event = store.record_initial(
        outcome, actor_id="operator-1", idempotency_key="initial-1"
    )

    with sqlite3.connect(path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE signal_outcome_events SET actor_id = 'tampered' WHERE event_id = ?",
                (str(event.event_id),),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM signal_outcome_events WHERE event_id = ?",
                (str(event.event_id),),
            )


def test_sqlite_outcome_event_idempotency_survives_restart(tmp_path):
    path = tmp_path / "outcomes.db"
    outcome = make_outcome()
    first = SQLiteOutcomeEventStore(path).record_initial(
        outcome, actor_id="operator-1", idempotency_key="initial-1"
    )
    replay = SQLiteOutcomeEventStore(path).record_initial(
        outcome, actor_id="operator-1", idempotency_key="initial-1"
    )
    assert replay == first



def test_sqlite_outcome_event_store_persists_credential_identity(tmp_path):
    path = tmp_path / "outcomes.db"
    author_credential = uuid4()
    reviewer_credential = uuid4()
    now = [datetime(2026, 10, 15, 12, tzinfo=timezone.utc)]
    store = SQLiteOutcomeEventStore(path, clock=lambda: now[0])
    original = store.record_initial(
        make_outcome(), actor_id="system:signal-lifecycle", idempotency_key="initial-1"
    )
    correction = store.submit_correction(
        make_outcome(original.signal_id, exit_price="96"),
        supersedes_event_id=original.event_id,
        actor_id="author-1",
        actor_credential_id=author_credential,
        idempotency_key="correction-1",
    )
    now[0] += timedelta(minutes=1)
    store.review_correction(
        correction.event_id,
        reviewer_id="reviewer-1",
        reviewer_credential_id=reviewer_credential,
        decision=OutcomeCorrectionDecision.ACCEPTED,
        idempotency_key="review-1",
    )

    reopened = SQLiteOutcomeEventStore(path, clock=lambda: now[0])
    events = reopened.events_for(original.signal_id)
    assert events[1].actor_credential_id == author_credential
    assert events[2].actor_credential_id == reviewer_credential
    assert reopened.outcome_as_of(original.signal_id, cutoff=now[0]) == correction

# Batched lookup regression coverage.

def test_sqlite_batched_outcomes_as_of_reads_multiple_signals_and_corrections(tmp_path):
    now = [dt.datetime(2026, 10, 15, 12, tzinfo=timezone.utc)]
    store = SQLiteOutcomeEventStore(tmp_path / "outcomes.db", clock=lambda: now[0])
    first_outcome = make_outcome()
    second_outcome = make_outcome()
    first = store.record_initial(
        first_outcome, actor_id="operator-1", idempotency_key="batch-initial-1"
    )
    second = store.record_initial(
        second_outcome, actor_id="operator-1", idempotency_key="batch-initial-2"
    )
    correction = store.submit_correction(
        make_outcome(first.signal_id, exit_price="96"),
        supersedes_event_id=first.event_id,
        actor_id="author-1",
        idempotency_key="batch-correction-1",
    )
    now[0] += timedelta(minutes=1)
    store.review_correction(
        correction.event_id,
        reviewer_id="reviewer-1",
        decision=OutcomeCorrectionDecision.ACCEPTED,
        idempotency_key="batch-review-1",
    )
    unresolved_signal_id = uuid4()

    before_review = store.outcomes_as_of(
        [first.signal_id, second.signal_id, unresolved_signal_id],
        cutoff=now[0] - timedelta(seconds=1),
    )
    after_review = store.outcomes_as_of(
        [first.signal_id, second.signal_id, unresolved_signal_id],
        cutoff=now[0],
    )

    assert before_review == {
        first.signal_id: first,
        second.signal_id: second,
    }
    assert after_review == {
        first.signal_id: correction,
        second.signal_id: second,
    }
    assert store.outcomes_as_of([], cutoff=now[0]) == {}


def test_sqlite_batched_outcome_lookup_requires_timezone_aware_cutoff(tmp_path):
    import pytest

    store = SQLiteOutcomeEventStore(tmp_path / "outcomes.db")
    naive_cutoff = dt.datetime(2026, 10, 15, 12)

    with pytest.raises(ValueError, match="cutoff must be timezone-aware"):
        store.outcomes_as_of([], cutoff=naive_cutoff)


def test_sqlite_batched_lookup_executes_one_filtered_select(tmp_path, monkeypatch):
    from app.infrastructure.persistence import sqlite_outcome_event_store as module

    now = dt.datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
    store = SQLiteOutcomeEventStore(tmp_path / "query-count.db", clock=lambda: now)
    first = store.record_initial(
        make_outcome(), actor_id="operator-1", idempotency_key="query-count-1"
    )
    second = store.record_initial(
        make_outcome(), actor_id="operator-1", idempotency_key="query-count-2"
    )
    statements = []
    original_connect = module.connect_sqlite

    def traced_connect(path):
        connection = original_connect(path)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(module, "connect_sqlite", traced_connect)

    result = store.outcomes_as_of(
        [first.signal_id, second.signal_id, uuid4()], cutoff=now
    )

    selects = [
        statement for statement in statements
        if statement.lstrip().upper().startswith("SELECT")
    ]
    assert set(result) == {first.signal_id, second.signal_id}
    assert len(selects) == 1
    assert "WHERE signal_id IN" in selects[0]


def test_sqlite_batched_lookup_falls_back_safely_above_parameter_limit(tmp_path, monkeypatch):
    from app.infrastructure.persistence import sqlite_outcome_event_store as module

    store = SQLiteOutcomeEventStore(tmp_path / "large-batch.db")
    statements = []
    original_connect = module.connect_sqlite

    def traced_connect(path):
        connection = original_connect(path)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(module, "connect_sqlite", traced_connect)
    signal_ids = [uuid4() for _ in range(901)]

    assert store.outcomes_as_of(
        signal_ids, cutoff=dt.datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
    ) == {}
    selects = [
        statement for statement in statements
        if statement.lstrip().upper().startswith("SELECT")
    ]
    assert len(selects) == 1
    assert "WHERE signal_id IN" not in selects[0]
