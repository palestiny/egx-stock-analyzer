from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.signals.outcome_event_store import InMemoryOutcomeEventStore
from app.domain.signals.model import SignalDirection
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord
from app.domain.signals.outcome_event import OutcomeCorrectionDecision, OutcomeEventKind


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


def test_late_recorded_outcome_is_not_visible_before_recorded_at():
    now = [datetime(2026, 10, 15, 12, tzinfo=timezone.utc)]
    store = InMemoryOutcomeEventStore(clock=lambda: now[0])
    outcome = make_outcome()

    event = store.record_initial(outcome, actor_id="operator-1", idempotency_key="initial-1")

    assert event.recorded_at == now[0]
    assert store.outcome_as_of(outcome.signal_id, cutoff=now[0] - timedelta(days=1)) is None
    assert store.outcome_as_of(outcome.signal_id, cutoff=now[0]) == event


def test_correction_requires_independent_review_and_is_as_of_aware():
    now = [datetime(2026, 10, 15, 12, tzinfo=timezone.utc)]
    store = InMemoryOutcomeEventStore(clock=lambda: now[0])
    original = store.record_initial(
        make_outcome(), actor_id="author-1", idempotency_key="initial-1"
    )
    correction = store.submit_correction(
        make_outcome(original.signal_id, exit_price="96"),
        supersedes_event_id=original.event_id,
        actor_id="author-2",
        idempotency_key="correction-1",
    )

    with pytest.raises(ValueError, match="cannot review their own"):
        store.review_correction(
            correction.event_id,
            reviewer_id="author-2",
            decision=OutcomeCorrectionDecision.ACCEPTED,
            idempotency_key="self-review",
        )

    assert store.outcome_as_of(original.signal_id, cutoff=now[0]) == original
    now[0] += timedelta(hours=1)
    review = store.review_correction(
        correction.event_id,
        reviewer_id="reviewer-1",
        decision=OutcomeCorrectionDecision.ACCEPTED,
        idempotency_key="review-1",
    )
    assert review.recorded_at == now[0]
    assert store.outcome_as_of(original.signal_id, cutoff=now[0] - timedelta(minutes=1)) == original
    assert store.outcome_as_of(original.signal_id, cutoff=now[0]) == correction


def test_rejected_correction_never_replaces_accepted_outcome():
    now = [datetime(2026, 10, 15, 12, tzinfo=timezone.utc)]
    store = InMemoryOutcomeEventStore(clock=lambda: now[0])
    original = store.record_initial(
        make_outcome(), actor_id="author-1", idempotency_key="initial-1"
    )
    correction = store.submit_correction(
        make_outcome(original.signal_id, exit_price="96"),
        supersedes_event_id=original.event_id,
        actor_id="author-2",
        idempotency_key="correction-1",
    )
    store.review_correction(
        correction.event_id,
        reviewer_id="reviewer-1",
        decision=OutcomeCorrectionDecision.REJECTED,
        idempotency_key="review-1",
    )

    assert store.outcome_as_of(original.signal_id, cutoff=now[0]) == original
    assert [event.kind for event in store.events_for(original.signal_id)] == [
        OutcomeEventKind.OUTCOME_RECORDED,
        OutcomeEventKind.CORRECTION_SUBMITTED,
        OutcomeEventKind.CORRECTION_REVIEWED,
    ]


def test_event_idempotency_rejects_conflicting_reuse():
    store = InMemoryOutcomeEventStore()
    outcome = make_outcome()
    first = store.record_initial(
        outcome, actor_id="operator-1", idempotency_key="same-key"
    )
    replay = store.record_initial(
        outcome, actor_id="operator-1", idempotency_key="same-key"
    )
    assert replay == first

    with pytest.raises(ValueError, match="idempotency key reused"):
        store.record_initial(
            make_outcome(outcome.signal_id, exit_price="97"),
            actor_id="operator-1",
            idempotency_key="same-key",
        )
