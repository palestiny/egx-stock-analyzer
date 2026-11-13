from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.alerts.in_memory import InMemoryAlertPublisher
from app.application.signals.lifecycle_orchestrator import SignalLifecycleOrchestrator
from app.application.signals.store import InMemorySignalHistoryStore
from app.application.signals.track_record import InMemoryTrackRecordStore
from app.domain.signals.lifecycle import (
    CompletedDailyBarObservation,
    SignalMarketState,
)
from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)


def make_signal() -> Signal:
    generated = datetime(2026, 10, 3, tzinfo=timezone.utc)
    return Signal(
        symbol="COMI",
        direction=SignalDirection.BUY,
        status=SignalStatus.ACTIVE,
        generated_at=generated,
        timeframe="DAILY",
        entry_zone=PriceZone(Decimal("99"), Decimal("101")),
        invalidation=Decimal("95"),
        targets=(Target(Decimal("109"), "T1"), Target(Decimal("113"), "T2")),
        confidence=Decimal("80"),
        risk_score=Decimal("20"),
        evidence=(SignalEvidence("trend", "test"),),
        strategy_id="breakout-trend",
        strategy_version="1.0",
        data_timestamp=generated,
    )


def test_orchestrator_coordinates_transition_alert_and_outcome():
    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    track_record = InMemoryTrackRecordStore()
    orchestrator = SignalLifecycleOrchestrator(history, alerts, track_record)

    signal = make_signal()
    observed_at = datetime(2026, 10, 4, 10, tzinfo=timezone.utc)
    data_timestamp = datetime(2026, 10, 4, 9, 55, tzinfo=timezone.utc)
    state = SignalMarketState(observed_at, Decimal("110"), data_timestamp)
    result = orchestrator.process(signal, state, entry_price=Decimal("100"))

    assert result.changed is True
    assert result.signal.status is SignalStatus.TRIGGERED
    assert result.alert_published is True
    assert result.outcome_recorded is True
    assert len(alerts.events) == 1

    outcome = track_record.get(result.signal_id)
    assert outcome is not None
    assert outcome.target_label == "T1"
    assert outcome.realized_return == Decimal("0.10")
    assert outcome.realized_r == Decimal("2")
    assert outcome.data_timestamp == data_timestamp
    assert outcome.data_timestamp != signal.data_timestamp
    assert outcome.data_timestamp != state.observed_at
    assert history.history(result.signal_id)[-1].event == "STATUS_TRIGGERED"


def test_reprocessing_same_observation_is_idempotent():
    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    track_record = InMemoryTrackRecordStore()
    orchestrator = SignalLifecycleOrchestrator(history, alerts, track_record)

    signal = make_signal()
    observed_at = datetime(2026, 10, 4, tzinfo=timezone.utc)
    state = SignalMarketState(observed_at, Decimal("110"), observed_at)

    first = orchestrator.process(signal, state, entry_price=Decimal("100"))
    second = orchestrator.process(signal, state, entry_price=Decimal("100"))

    assert second.signal_id == first.signal_id
    assert second.changed is False
    assert len(alerts.events) == 1
    assert len(track_record.all()) == 1
    assert len(history.history(first.signal_id)) == 2


def test_sell_outcome_uses_direction_aware_return_and_r():
    signal = Signal(
        **{
            **make_signal().__dict__,
            "direction": SignalDirection.SELL,
            "invalidation": Decimal("105"),
            "targets": (Target(Decimal("91"), "T1"), Target(Decimal("87"), "T2")),
        }
    )
    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    track_record = InMemoryTrackRecordStore()
    orchestrator = SignalLifecycleOrchestrator(history, alerts, track_record)

    result = orchestrator.process(
        signal,
        SignalMarketState(
            datetime(2026, 10, 4, tzinfo=timezone.utc),
            Decimal("90"),
            datetime(2026, 10, 4, tzinfo=timezone.utc),
        ),
        entry_price=Decimal("100"),
    )

    outcome = track_record.get(result.signal_id)
    assert outcome is not None
    assert outcome.realized_return == Decimal("0.10")
    assert outcome.realized_r == Decimal("2")


def test_changed_supporting_evidence_invalidates_prior_signal_without_trade_outcome():
    from dataclasses import replace

    from app.domain.signals.model import SignalEvidence, SignalStatus

    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    track_record = InMemoryTrackRecordStore()
    orchestrator = SignalLifecycleOrchestrator(history, alerts, track_record)
    original = make_signal()
    created = history.record(original, "CREATED", original.generated_at)
    revised_candidate = replace(
        original,
        evidence=(SignalEvidence("trend", "trend no longer confirms"),),
        generated_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
        data_timestamp=datetime(2026, 10, 5, tzinfo=timezone.utc),
    )

    result = orchestrator.invalidate_for_evidence_change(
        revised_candidate,
        observed_at=datetime(2026, 10, 4, 1, tzinfo=timezone.utc),
    )

    assert result is not None
    assert result.signal_id == created.signal_id
    assert result.changed is True
    assert result.signal.status is SignalStatus.INVALIDATED
    assert result.outcome_recorded is False
    assert result.alert_published is True
    assert len(alerts.events) == 1
    assert len(track_record.all()) == 0
    assert history.history(created.signal_id)[-1].event == "EVIDENCE_CHANGED_INVALIDATED"


def test_unchanged_or_missing_candidate_does_not_invalidate_signal():
    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    track_record = InMemoryTrackRecordStore()
    orchestrator = SignalLifecycleOrchestrator(history, alerts, track_record)
    original = make_signal()
    created = history.record(original, "CREATED", original.generated_at)

    unchanged = orchestrator.invalidate_for_evidence_change(
        original,
        observed_at=datetime(2026, 10, 4, 1, tzinfo=timezone.utc),
    )
    missing = orchestrator.invalidate_for_evidence_change(
        None,
        observed_at=datetime(2026, 10, 4, 1, tzinfo=timezone.utc),
    )

    assert unchanged is not None
    assert unchanged.changed is False
    assert missing is None
    assert history.history(created.signal_id) == (created,)
    assert alerts.events == []


def test_evidence_change_does_not_reopen_or_reinvalidate_terminal_signal():
    from dataclasses import replace

    from app.domain.signals.model import SignalEvidence, SignalStatus

    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    track_record = InMemoryTrackRecordStore()
    orchestrator = SignalLifecycleOrchestrator(history, alerts, track_record)
    original = make_signal()
    terminal = replace(original, status=SignalStatus.INVALIDATED)
    created = history.record(terminal, "STATUS_INVALIDATED", terminal.generated_at)
    revised_candidate = replace(
        original,
        evidence=(SignalEvidence("trend", "different evidence"),),
        generated_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
        data_timestamp=datetime(2026, 10, 5, tzinfo=timezone.utc),
    )

    result = orchestrator.invalidate_for_evidence_change(
        revised_candidate,
        observed_at=datetime(2026, 10, 4, 1, tzinfo=timezone.utc),
    )

    assert result is None
    assert history.history(created.signal_id) == (created,)
    assert alerts.events == []


def test_new_evaluation_timestamp_alone_does_not_invalidate_same_setup():
    from dataclasses import replace

    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    track_record = InMemoryTrackRecordStore()
    orchestrator = SignalLifecycleOrchestrator(history, alerts, track_record)
    original = make_signal()
    created = history.record(original, "CREATED", original.generated_at)
    next_evaluation = replace(
        original,
        generated_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
    )

    result = orchestrator.invalidate_for_evidence_change(
        next_evaluation,
        observed_at=datetime(2026, 10, 5, 1, tzinfo=timezone.utc),
    )

    assert result is not None
    assert result.changed is False
    assert result.signal_id == created.signal_id
    assert history.history(created.signal_id) == (created,)
    assert alerts.events == []


def test_orchestrator_rejects_non_finite_entry_price() -> None:
    orchestrator = SignalLifecycleOrchestrator(
        InMemorySignalHistoryStore(),
        InMemoryAlertPublisher(),
        InMemoryTrackRecordStore(),
    )
    with pytest.raises(ValueError, match="finite and positive"):
        orchestrator.process(
            make_signal(),
            SignalMarketState(
                datetime(2026, 10, 4, tzinfo=timezone.utc),
                Decimal("100"),
                datetime(2026, 10, 4, tzinfo=timezone.utc),
            ),
            entry_price=Decimal("NaN"),
        )


def test_orchestrator_rejects_pre_generation_observation_before_writing_history() -> None:
    history = InMemorySignalHistoryStore()
    orchestrator = SignalLifecycleOrchestrator(
        history,
        InMemoryAlertPublisher(),
        InMemoryTrackRecordStore(),
    )
    with pytest.raises(ValueError, match="cannot precede"):
        orchestrator.process(
            make_signal(),
            SignalMarketState(
                datetime(2026, 10, 2, tzinfo=timezone.utc),
                Decimal("100"),
                datetime(2026, 10, 2, tzinfo=timezone.utc),
            ),
            entry_price=Decimal("100"),
        )
    assert history.all_records() == ()


def make_completed_bar(*, high="105", low="98", observed_hour=16, revision="r1", candle_day=4):
    return CompletedDailyBarObservation(
        symbol="COMI",
        provider="attested-provider",
        timeframe="DAILY",
        candle_at=datetime(2026, 10, candle_day, tzinfo=timezone.utc),
        observed_at=datetime(2026, 10, candle_day, observed_hour, tzinfo=timezone.utc),
        revision=revision,
        source_reference=f"https://provider.example/COMI/2026-10-{candle_day:02d}",
        finality_attestation="provider-finality-assertion",
        is_final=True,
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal("102"),
    )


def test_completed_daily_bar_records_level_observation_without_assumed_entry_or_outcome():
    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    outcomes = InMemoryTrackRecordStore()
    signal = make_signal()
    published = history.record(signal, "PUBLISHED", signal.generated_at)
    orchestrator = SignalLifecycleOrchestrator(history, alerts, outcomes)

    result = orchestrator.process_completed_daily_bar(published.signal_id, make_completed_bar(), calendar_version="calendar-v1")

    assert result is not None
    assert result.changed is False
    assert result.outcome_recorded is False
    assert result.alert_published is False
    assert outcomes.all() == ()
    assert alerts.events == []


def test_completed_daily_bar_triggers_and_publishes_without_performance_accounting():
    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    outcomes = InMemoryTrackRecordStore()
    signal = make_signal()
    published = history.record(signal, "PUBLISHED", signal.generated_at)
    orchestrator = SignalLifecycleOrchestrator(history, alerts, outcomes)

    result = orchestrator.process_completed_daily_bar(
        published.signal_id, make_completed_bar(high="109", low="98"), calendar_version="calendar-v1"
    )

    assert result is not None
    assert result.changed is True
    assert result.signal.status is SignalStatus.TRIGGERED
    assert result.outcome_recorded is False
    assert result.alert_published is True
    assert outcomes.all() == ()
    assert len(alerts.events) == 1
    replay = orchestrator.process_completed_daily_bar(
        published.signal_id,
        make_completed_bar(high="109", low="98"),
        calendar_version="calendar-v1",
    )
    assert replay is not None and replay.changed is False
    assert len(alerts.events) == 1


def test_completed_daily_bar_replay_is_idempotent_even_if_retrieved_again_later():
    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    outcomes = InMemoryTrackRecordStore()
    signal = make_signal()
    published = history.record(signal, "PUBLISHED", signal.generated_at)
    orchestrator = SignalLifecycleOrchestrator(history, alerts, outcomes)

    first_bar = make_completed_bar()
    first = orchestrator.process_completed_daily_bar(published.signal_id, first_bar, calendar_version="calendar-v1")
    replay = orchestrator.process_completed_daily_bar(
        published.signal_id, make_completed_bar(observed_hour=17), calendar_version="calendar-v1"
    )

    assert first is not None and replay is not None
    assert first.signal_id == replay.signal_id
    assert replay.changed is False
    assert len(history.history(first.signal_id)) == 1
    assert outcomes.all() == ()


def test_completed_daily_bar_rejects_out_of_order_and_conflicting_same_identity():
    history = InMemorySignalHistoryStore()
    orchestrator = SignalLifecycleOrchestrator(
        history, InMemoryAlertPublisher(), InMemoryTrackRecordStore()
    )
    signal = make_signal()
    published = history.record(signal, "PUBLISHED", signal.generated_at)
    orchestrator.process_completed_daily_bar(published.signal_id, make_completed_bar(), calendar_version="calendar-v1")

    with pytest.raises(ValueError, match="conflicting replay"):
        orchestrator.process_completed_daily_bar(
            published.signal_id, make_completed_bar(high="106", observed_hour=17), calendar_version="calendar-v1"
        )

    later = CompletedDailyBarObservation(
        symbol="COMI",
        provider="attested-provider",
        timeframe="DAILY",
        candle_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
        observed_at=datetime(2026, 10, 5, 16, tzinfo=timezone.utc),
        revision="r1",
        source_reference="https://provider.example/COMI/2026-10-05",
        finality_attestation="provider-finality-assertion",
        is_final=True,
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("98"),
        close=Decimal("102"),
    )
    orchestrator.process_completed_daily_bar(published.signal_id, later, calendar_version="calendar-v1")
    replay = orchestrator.process_completed_daily_bar(published.signal_id, make_completed_bar(), calendar_version="calendar-v1")
    assert replay is not None and replay.changed is False
    with pytest.raises(ValueError, match="out-of-order"):
        orchestrator.process_completed_daily_bar(published.signal_id, make_completed_bar(candle_day=3), calendar_version="calendar-v1")


def test_same_completed_bar_can_be_evaluated_for_multiple_opportunities_on_one_symbol():
    from dataclasses import replace

    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    outcomes = InMemoryTrackRecordStore()
    first_signal = make_signal()
    second_signal = replace(
        make_signal(),
        strategy_id="range-breakout",
        targets=(Target(Decimal("120"), "T1"),),
    )
    first = history.record(first_signal, "PUBLISHED", first_signal.generated_at)
    second = history.record(second_signal, "PUBLISHED", second_signal.generated_at)
    orchestrator = SignalLifecycleOrchestrator(history, alerts, outcomes)
    bar = make_completed_bar(high="109", low="98")

    first_result = orchestrator.process_completed_daily_bar(
        first.signal_id, bar, calendar_version="calendar-v1"
    )
    second_result = orchestrator.process_completed_daily_bar(
        second.signal_id, bar, calendar_version="calendar-v1"
    )

    assert first_result is not None
    assert first_result.signal.status is SignalStatus.TRIGGERED
    assert second_result is not None
    assert second_result.signal.status is SignalStatus.ACTIVE
    assert len(alerts.events) == 1
    assert outcomes.all() == ()


def test_opportunity_expires_after_twenty_eligible_sessions_without_performance_outcome():
    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    outcomes = InMemoryTrackRecordStore()
    signal = make_signal()
    published = history.record(signal, "PUBLISHED", signal.generated_at)
    orchestrator = SignalLifecycleOrchestrator(history, alerts, outcomes)
    sessions = tuple(date(2026, 10, day) for day in range(1, 21))

    expired = orchestrator.expire_opportunity(
        published.signal_id,
        eligible_sessions=sessions,
        calendar_version="calendar-v1",
        evaluated_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
    )

    assert expired is not None
    assert expired.signal.status is SignalStatus.EXPIRED
    assert expired.outcome_recorded is False
    assert expired.alert_published is True
    assert len(alerts.events) == 1
    assert alerts.events[0].event_type.value == "SIGNAL_EXPIRED"
    assert outcomes.all() == ()
    assert history.history(published.signal_id)[-1].event == "STATUS_EXPIRED"


def test_opportunity_cannot_expire_before_twenty_eligible_sessions():
    orchestrator = SignalLifecycleOrchestrator(
        InMemorySignalHistoryStore(),
        InMemoryAlertPublisher(),
        InMemoryTrackRecordStore(),
    )
    with pytest.raises(ValueError, match="20 eligible sessions"):
        orchestrator.expire_opportunity(
            uuid4(),
            eligible_sessions=tuple(date(2026, 10, day) for day in range(1, 20)),
            calendar_version="calendar-v1",
            evaluated_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
        )


def test_gap_resolution_rolls_back_when_alert_publication_fails():
    class FailingAlertPublisher(InMemoryAlertPublisher):
        def publish(self, event):
            raise RuntimeError("simulated outbox failure")

    history = InMemorySignalHistoryStore()
    alerts = FailingAlertPublisher()
    outcomes = InMemoryTrackRecordStore()
    signal = make_signal()
    published = history.record(signal, "PUBLISHED", signal.generated_at)
    orchestrator = SignalLifecycleOrchestrator(history, alerts, outcomes)
    bar = make_completed_bar(high="109")

    gap = orchestrator.mark_session_gap(
        published.signal_id,
        session_date=bar.candle_at.date(),
        calendar_version="calendar-v1",
        reason="MISSING_ELIGIBLE_BAR",
        detected_at=bar.observed_at,
    )

    with pytest.raises(RuntimeError, match="simulated outbox failure"):
        orchestrator.process_completed_daily_bar(
            published.signal_id,
            bar,
            calendar_version="calendar-v1",
            resolved_gap_session_date=bar.candle_at.date(),
        )

    assert orchestrator.session_gap_events(published.signal_id) == (gap,)
    assert orchestrator.latest_completed_observation(published.signal_id) is None
    assert history.get(published.signal_id).signal.status is SignalStatus.ACTIVE
