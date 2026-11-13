from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
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
from app.application.signals.lifecycle_orchestrator import SignalLifecycleOrchestrator
from app.domain.signals.lifecycle import (
    CompletedDailyBarObservation,
    SignalMarketState,
)
from app.application.signals.lifecycle_unit_of_work import LifecycleObservationRecord
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord
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
        status=SignalStatus.ACTIVE,
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
        terminal = replace(signal, status=SignalStatus.TRIGGERED)
        transaction.record_signal(terminal, "STATUS_TRIGGERED", OBSERVED)
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
        terminal = replace(signal, status=SignalStatus.TRIGGERED)
        transaction.record_signal(terminal, "STATUS_TRIGGERED", OBSERVED)
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



def test_sqlite_orchestrator_serializes_concurrent_replays(tmp_path):
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

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(
            executor.map(
                lambda _: orchestrator.process(
                    signal, state, entry_price=Decimal("100")
                ),
                range(2),
            )
        )

    assert sum(result.changed for result in results) == 1
    signal_id = results[0].signal_id
    assert results[1].signal_id == signal_id
    assert len(history.history(signal_id)) == 2
    assert len(track_record.all()) == 1
    assert len(outbox.pending()) == 1


def test_sqlite_evidence_invalidation_commits_history_and_alert_without_outcome(tmp_path):
    unit_of_work, history, track_record, outbox = make_unit_of_work(
        tmp_path / "analysis.db"
    )
    signal = make_signal()
    created = history.record(signal, "CREATED", GENERATED)
    orchestrator = SignalLifecycleOrchestrator(
        history=history,
        alerts=outbox,
        track_record=track_record,
        unit_of_work=unit_of_work,
    )
    candidate = replace(
        signal,
        evidence=(SignalEvidence("trend", "supporting evidence changed"),),
    )

    result = orchestrator.invalidate_for_evidence_change(
        candidate, observed_at=OBSERVED
    )

    assert result is not None
    assert result.changed is True
    assert result.signal_id == created.signal_id
    assert history.history(created.signal_id)[-1].event == "EVIDENCE_CHANGED_INVALIDATED"
    assert len(outbox.pending()) == 1
    assert track_record.all() == ()



@pytest.mark.parametrize(
    "failure_stage",
    ("after_history", "after_outcome", "after_outbox"),
)
def test_sqlite_lifecycle_rolls_back_at_each_write_boundary(tmp_path, failure_stage):
    unit_of_work, history, track_record, outbox = make_unit_of_work(
        tmp_path / f"{failure_stage}.db"
    )
    signal = make_signal()

    def persist_until_failure(transaction):
        created = transaction.record_signal(signal, "CREATED", GENERATED)
        terminal = replace(signal, status=SignalStatus.TRIGGERED)
        transaction.record_signal(terminal, "STATUS_TRIGGERED", OBSERVED)
        if failure_stage == "after_history":
            raise RuntimeError(f"failure at {failure_stage}")

        transaction.record_outcome(
            SignalOutcomeRecord(
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
        )
        if failure_stage == "after_outcome":
            raise RuntimeError(f"failure at {failure_stage}")

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
        raise RuntimeError(f"failure at {failure_stage}")

    with pytest.raises(RuntimeError, match=f"failure at {failure_stage}"):
        unit_of_work.execute(persist_until_failure)

    assert history.all_records() == ()
    assert track_record.all() == ()
    assert outbox.pending() == ()


def make_completed_bar(*, high="105", observed_hour=16):
    return CompletedDailyBarObservation(
        symbol="COMI",
        provider="attested-provider",
        timeframe="DAILY",
        candle_at=datetime(2026, 10, 4, tzinfo=timezone.utc),
        observed_at=datetime(2026, 10, 4, observed_hour, tzinfo=timezone.utc),
        revision="r1",
        source_reference="https://provider.example/COMI/2026-10-04",
        finality_attestation="provider-finality-assertion",
        is_final=True,
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal("98"),
        close=Decimal("102"),
    )


def test_sqlite_completed_daily_observation_is_durable_and_idempotent(tmp_path):
    database = tmp_path / "daily-observations.db"
    unit_of_work, history, track_record, outbox = make_unit_of_work(database)
    signal = make_signal()
    published = history.record(signal, "PUBLISHED", GENERATED)
    orchestrator = SignalLifecycleOrchestrator(
        history=history,
        alerts=outbox,
        track_record=track_record,
        unit_of_work=unit_of_work,
    )
    first_bar = make_completed_bar()
    first = orchestrator.process_completed_daily_bar(published.signal_id, first_bar, calendar_version="calendar-v1")
    assert first is not None and first.changed is False

    reopened_history = SQLiteSignalHistoryStore(database)
    reopened_track_record = SQLiteTrackRecordStore(database)
    reopened_outbox = SQLiteAlertOutbox(database)
    reopened_uow = SQLiteSignalLifecycleUnitOfWork(
        reopened_history, reopened_track_record, reopened_outbox
    )
    reopened = SignalLifecycleOrchestrator(
        history=reopened_history,
        alerts=reopened_outbox,
        track_record=reopened_track_record,
        unit_of_work=reopened_uow,
    )
    replay = reopened.process_completed_daily_bar(
        published.signal_id, make_completed_bar(observed_hour=17), calendar_version="calendar-v1"
    )

    assert replay is not None
    assert replay.changed is False
    stored = reopened_uow.execute(
        lambda transaction: transaction.get_observation(published.signal_id, first_bar.identity)
    )
    assert stored is not None
    assert stored.bar.high == Decimal("105")
    assert stored.resulting_status is SignalStatus.ACTIVE
    assert reopened_track_record.all() == ()
    assert reopened_outbox.pending() == ()


def test_sqlite_daily_observation_ledger_rolls_back_with_lifecycle_transaction(tmp_path):
    unit_of_work, history, track_record, outbox = make_unit_of_work(
        tmp_path / "daily-observation-rollback.db"
    )
    signal = make_signal()
    created = history.record(signal, "PUBLISHED", GENERATED)
    bar = make_completed_bar()

    def fail_after_observation(transaction):
        transaction.record_observation(
            LifecycleObservationRecord(
                signal_id=created.signal_id,
                bar=bar,
                policy_version="dec138-daily-ohlc-v1",
                calendar_version="calendar-v1",
                resulting_status=SignalStatus.ACTIVE,
            )
        )
        raise RuntimeError("simulated observation transaction failure")

    with pytest.raises(RuntimeError, match="simulated observation"):
        unit_of_work.execute(fail_after_observation)

    assert unit_of_work.execute(
        lambda transaction: transaction.get_observation(created.signal_id, bar.identity)
    ) is None


def test_sqlite_daily_observation_ledger_is_append_only(tmp_path):
    unit_of_work, history, track_record, outbox = make_unit_of_work(
        tmp_path / "daily-observation-append-only.db"
    )
    signal = make_signal()
    created = history.record(signal, "PUBLISHED", GENERATED)
    bar = make_completed_bar()
    unit_of_work.execute(
        lambda transaction: transaction.record_observation(
            LifecycleObservationRecord(
                signal_id=created.signal_id,
                bar=bar,
                policy_version="dec138-daily-ohlc-v1",
                calendar_version="calendar-v1",
                resulting_status=SignalStatus.ACTIVE,
            )
        )
    )

    import sqlite3

    connection = sqlite3.connect(str(tmp_path / "daily-observation-append-only.db"))
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM signal_lifecycle_daily_observations"
            )
    finally:
        connection.close()


def test_sqlite_lifecycle_transition_stays_on_revised_opportunity_identity(tmp_path):
    database = tmp_path / "revision-lifecycle.db"
    unit_of_work, history, track_record, outbox = make_unit_of_work(database)
    original = make_signal()
    parent = history.record(original, "PUBLISHED", GENERATED)
    revised = replace(
        original,
        targets=(Target(Decimal("108"), "T1"),),
        evidence=(SignalEvidence("trend", "revised evidence"),),
    )
    child = history.record_revision(
        revised,
        "PUBLISHED_VERSION",
        GENERATED + timedelta(minutes=1),
        parent_signal_id=parent.signal_id,
        reason="Material target and evidence change",
    )
    orchestrator = SignalLifecycleOrchestrator(
        history=history,
        alerts=outbox,
        track_record=track_record,
        unit_of_work=unit_of_work,
    )

    result = orchestrator.process_completed_daily_bar(
        child.signal_id,
        make_completed_bar(high="109"),
        calendar_version="calendar-v1",
    )

    assert result is not None
    assert result.signal_id == child.signal_id
    assert result.signal.status is SignalStatus.TRIGGERED
    assert history.get(parent.signal_id).signal.status is SignalStatus.ACTIVE
    assert history.get(child.signal_id).signal.status is SignalStatus.TRIGGERED
    assert history.revision_link(child.signal_id).parent_signal_id == parent.signal_id
    assert track_record.all() == ()


def test_sqlite_correction_is_append_only_and_does_not_rewrite_lifecycle_outcome(tmp_path):
    database = tmp_path / "daily-bar-correction.db"
    unit_of_work, history, track_record, outbox = make_unit_of_work(database)
    signal = make_signal()
    published = history.record(signal, "PUBLISHED", GENERATED)
    orchestrator = SignalLifecycleOrchestrator(
        history=history,
        alerts=outbox,
        track_record=track_record,
        unit_of_work=unit_of_work,
    )
    original_bar = make_completed_bar()
    orchestrator.process_completed_daily_bar(
        published.signal_id,
        original_bar,
        calendar_version="calendar-v1",
    )
    corrected_bar = replace(
        original_bar,
        revision="r2",
        source_reference="https://provider.example/COMI/2026-10-04/revision-2",
        finality_attestation="provider-finality-v2",
        high=Decimal("109"),
        observed_at=original_bar.observed_at + timedelta(hours=1),
    )

    correction = orchestrator.record_daily_bar_correction(
        published.signal_id,
        original_identity=original_bar.identity,
        corrected_bar=corrected_bar,
        operator_id="operator-1",
        reason="Provider published a corrected daily candle",
        calendar_version="calendar-v1",
        recorded_at=corrected_bar.observed_at,
    )
    replay = orchestrator.record_daily_bar_correction(
        published.signal_id,
        original_identity=original_bar.identity,
        corrected_bar=corrected_bar,
        operator_id="operator-1",
        reason="Provider published a corrected daily candle",
        calendar_version="calendar-v1",
        recorded_at=corrected_bar.observed_at,
    )

    assert replay == correction
    assert correction.status == "RECORDED_NOT_REEVALUATED"
    assert orchestrator.lifecycle_corrections(published.signal_id) == (correction,)
    original = orchestrator.latest_completed_observation(published.signal_id)
    assert original.bar.revision == "r1"
    assert original.bar.high == Decimal("105")
    assert history.get(published.signal_id).signal.status is SignalStatus.ACTIVE
    assert track_record.all() == ()
    import sqlite3
    connection = sqlite3.connect(str(database))
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM signal_lifecycle_daily_bar_corrections WHERE correction_id = ?",
                (str(correction.correction_id),),
            )
    finally:
        connection.close()


def test_sqlite_correction_ledger_rejects_same_revision_as_original(tmp_path):
    database = tmp_path / "daily-bar-correction-invalid.db"
    unit_of_work, history, track_record, outbox = make_unit_of_work(database)
    signal = make_signal()
    published = history.record(signal, "PUBLISHED", GENERATED)
    orchestrator = SignalLifecycleOrchestrator(
        history=history,
        alerts=outbox,
        track_record=track_record,
        unit_of_work=unit_of_work,
    )
    original_bar = make_completed_bar()
    orchestrator.process_completed_daily_bar(
        published.signal_id,
        original_bar,
        calendar_version="calendar-v1",
    )

    with pytest.raises(ValueError, match="new source revision"):
        orchestrator.record_daily_bar_correction(
            published.signal_id,
            original_identity=original_bar.identity,
            corrected_bar=original_bar,
            operator_id="operator-1",
            reason="No revision change",
            calendar_version="calendar-v1",
            recorded_at=original_bar.observed_at,
        )


def test_sqlite_session_gap_events_are_durable_and_append_only(tmp_path):
    import sqlite3

    database = tmp_path / "session-gap-ledger.db"
    unit_of_work, history, track_record, outbox = make_unit_of_work(database)
    signal = make_signal()
    published = history.record(signal, "PUBLISHED", GENERATED)
    orchestrator = SignalLifecycleOrchestrator(
        history=history,
        alerts=outbox,
        track_record=track_record,
        unit_of_work=unit_of_work,
    )
    gap_date = date(2026, 10, 5)
    stale = orchestrator.mark_session_gap(
        published.signal_id,
        session_date=gap_date,
        calendar_version="calendar-v1",
        reason="MISSING_ELIGIBLE_BAR",
        detected_at=GENERATED + timedelta(days=2),
    )
    resolved = orchestrator.resolve_session_gap(
        published.signal_id,
        session_date=gap_date,
        calendar_version="calendar-v1",
        reason="ELIGIBLE_BAR_RECONCILED",
        resolved_at=GENERATED + timedelta(days=3),
    )
    assert stale.status == "STALE"
    assert resolved is not None and resolved.status == "RESOLVED"

    reopened_history = SQLiteSignalHistoryStore(database)
    reopened_track_record = SQLiteTrackRecordStore(database)
    reopened_outbox = SQLiteAlertOutbox(database)
    reopened_uow = SQLiteSignalLifecycleUnitOfWork(
        reopened_history, reopened_track_record, reopened_outbox
    )
    reopened = SignalLifecycleOrchestrator(
        history=reopened_history,
        alerts=reopened_outbox,
        track_record=reopened_track_record,
        unit_of_work=reopened_uow,
    )
    assert [event.status for event in reopened.session_gap_events(published.signal_id)] == [
        "STALE",
        "RESOLVED",
    ]

    connection = sqlite3.connect(str(database))
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM signal_lifecycle_session_gap_events WHERE event_id = ?",
                (str(stale.event_id),),
            )
    finally:
        connection.close()
