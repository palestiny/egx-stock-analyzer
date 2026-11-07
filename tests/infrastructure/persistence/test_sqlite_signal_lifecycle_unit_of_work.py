from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.alerts.model import AlertEvent, AlertEventType
from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord
from app.application.signals.lifecycle_orchestrator import SignalLifecycleOrchestrator
from app.domain.signals.lifecycle import SignalMarketState
from app.infrastructure.notifications.sqlite_alert_outbox import SQLiteAlertOutbox
from app.infrastructure.persistence.sqlite_signal_history_store import SQLiteSignalHistoryStore
from app.infrastructure.persistence.sqlite_signal_lifecycle_unit_of_work import (
    SQLiteSignalLifecycleUnitOfWork,
)
from app.infrastructure.persistence.sqlite_track_record_store import SQLiteTrackRecordStore


GENERATED = datetime(2026, 10, 3, tzinfo=timezone.utc)
OBSERVED = datetime(2026, 10, 4, 10, tzinfo=timezone.utc)


def make_signal() -> Signal:
    return Signal(
        symbol="COMI",
        direction=SignalDirection.BUY,
        status=SignalStatus.TRIGGERED,
        generated_at=GENERATED,
        timeframe="DAILY",
        entry_zone=PriceZone(Decimal("99"), Decimal("101")),
        invalidation=Decimal("95"),
        targets=(Target(Decimal("109"), "T1"),),
        confidence=Decimal("80"),
        risk_score=Decimal("20"),
        evidence=(SignalEvidence("trend", "verified trend evidence"),),
        strategy_id="breakout-trend",
        strategy_version="1.0",
        data_timestamp=GENERATED,
    )


def make_unit_of_work(database):
    history = SQLiteSignalHistoryStore(database)
    track_record = SQLiteTrackRecordStore(database)
    outbox = SQLiteAlertOutbox(database)
    return (
        SQLiteSignalLifecycleUnitOfWork(history, track_record, outbox),
        history,
        track_record,
        outbox,
    )


def test_lifecycle_unit_of_work_commits_history_outcome_and_outbox_together(tmp_path):
    database = tmp_path / "analysis.db"
    unit_of_work, history, track_record, outbox = make_unit_of_work(database)
    signal = make_signal()

    def persist(transaction):
        created = transaction.record_signal(signal, "CREATED", GENERATED)
        transaction.record_signal(signal, "STATUS_TRIGGERED", OBSERVED)
        outcome = SignalOutcomeRecord(
            signal_id=created.signal_id,
            symbol="COMI",
            outcome=SignalOutcome.TARGET_HIT,
            direction=SignalDirection.BUY,
            observed_at=OBSERVED,
            entry_price=Decimal("100"),
            exit_price=Decimal("110"),
            realized_return=Decimal("0.10"),
            realized_r=Decimal("2"),
            invalidation=Decimal("95"),
            target_label="T1",
            strategy_id="breakout-trend",
            strategy_version="1.0",
            data_timestamp=datetime(2026, 10, 4, 9, 55, tzinfo=timezone.utc),
        )
        transaction.record_outcome(outcome)
        event = AlertEvent(
            event_id=uuid4(),
            signal_id=created.signal_id,
            symbol="COMI",
            event_type=AlertEventType.SIGNAL_TRIGGERED,
            occurred_at=OBSERVED,
            message="COMI signal triggered",
        )
        transaction.publish_alert(event)
        return created.signal_id, event.event_id

    signal_id, event_id = unit_of_work.execute(persist)

    assert len(history.history(signal_id)) == 2
    assert track_record.get(signal_id) is not None
    assert outbox.get(event_id) is not None


def test_lifecycle_unit_of_work_rolls_back_all_writes_on_failure(tmp_path):
    unit_of_work, history, track_record, outbox = make_unit_of_work(
        tmp_path / "analysis.db"
    )
    signal = make_signal()

    def fail_after_all_writes(transaction):
        created = transaction.record_signal(signal, "CREATED", GENERATED)
        transaction.record_signal(signal, "STATUS_TRIGGERED", OBSERVED)
        outcome = SignalOutcomeRecord(
            signal_id=created.signal_id,
            symbol="COMI",
            outcome=SignalOutcome.TARGET_HIT,
            direction=SignalDirection.BUY,
            observed_at=OBSERVED,
            entry_price=Decimal("100"),
            exit_price=Decimal("110"),
            realized_return=Decimal("0.10"),
            realized_r=Decimal("2"),
            invalidation=Decimal("95"),
            target_label="T1",
            strategy_id="breakout-trend",
            strategy_version="1.0",
            data_timestamp=datetime(2026, 10, 4, 9, 55, tzinfo=timezone.utc),
        )
        transaction.record_outcome(outcome)
        transaction.publish_alert(
            AlertEvent(
                event_id=uuid4(),
                signal_id=created.signal_id,
                symbol="COMI",
                event_type=AlertEventType.SIGNAL_TRIGGERED,
                occurred_at=OBSERVED,
                message="COMI signal triggered",
            )
        )
        raise RuntimeError("simulated failure before commit")

    with pytest.raises(RuntimeError, match="simulated failure"):
        unit_of_work.execute(fail_after_all_writes)

    assert history.all_records() == ()
    assert track_record.all() == ()
    assert outbox.pending() == ()


def test_lifecycle_unit_of_work_requires_all_stores_to_share_database(tmp_path):
    history = SQLiteSignalHistoryStore(tmp_path / "history.db")
    track_record = SQLiteTrackRecordStore(tmp_path / "outcomes.db")
    outbox = SQLiteAlertOutbox(tmp_path / "outbox.db")

    with pytest.raises(ValueError, match="share one SQLite database"):
        SQLiteSignalLifecycleUnitOfWork(history, track_record, outbox)



def test_sqlite_orchestrator_replay_keeps_one_atomic_lifecycle_event(tmp_path):
    unit_of_work, history, track_record, outbox = make_unit_of_work(
        tmp_path / "analysis.db"
    )
    signal = make_signal()
    orchestrator = SignalLifecycleOrchestrator(
        history=history,
        alerts=outbox,
        track_record=track_record,
        unit_of_work=unit_of_work,
    )
    state = SignalMarketState(
        observed_at=OBSERVED,
        price=Decimal("110"),
        data_timestamp=datetime(2026, 10, 4, 9, 55, tzinfo=timezone.utc),
    )

    first = orchestrator.process(signal, state, entry_price=Decimal("100"))
    replay = orchestrator.process(signal, state, entry_price=Decimal("100"))

    assert first.changed is True
    assert first.outcome_recorded is True
    assert replay.changed is False
    assert replay.signal_id == first.signal_id
    assert len(history.history(first.signal_id)) == 2
    assert len(track_record.all()) == 1
    assert len(outbox.pending()) == 1
