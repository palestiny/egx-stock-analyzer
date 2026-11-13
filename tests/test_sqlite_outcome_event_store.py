import datetime as dt
from datetime import timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.domain.signals.model import SignalDirection
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord
from app.domain.signals.outcome_event import OutcomeCorrectionDecision
from app.infrastructure.persistence.sqlite_outcome_event_store import SQLiteOutcomeEventStore


def make_outcome(signal_id=None, *, exit_price="95"):
    observed_at = dt.datetime(2026, 10, 10, 10, tzinfo=timezone.utc)
    return SignalOutcomeRecord(
        signal_id=signal_id or uuid4(),
        symbol="EGAL",
        outcome=SignalOutcome.INVALIDATED,
        direction=SignalDirection.BUY,
        observed_at=observed_at,
        entry_price=Decimal("100"),
        exit_price=Decimal(exit_price),
        realized_return=Decimal("-0.05"),
        realized_r=Decimal("-1"),
        invalidation=Decimal("95"),
        target_label=None,
        strategy_id="trend",
        strategy_version="1",
        data_timestamp=observed_at,
    )


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
