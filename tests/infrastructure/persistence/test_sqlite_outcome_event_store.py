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
