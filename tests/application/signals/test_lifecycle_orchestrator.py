from datetime import datetime, timezone
from decimal import Decimal

from app.application.alerts.in_memory import InMemoryAlertPublisher
from app.application.signals.lifecycle_orchestrator import SignalLifecycleOrchestrator
from app.application.signals.store import InMemorySignalHistoryStore
from app.application.signals.track_record import InMemoryTrackRecordStore
from app.domain.signals.lifecycle import SignalMarketState
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
    state = SignalMarketState(
        datetime(2026, 10, 4, tzinfo=timezone.utc), Decimal("110")
    )
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
    assert history.history(result.signal_id)[-1].event == "STATUS_TRIGGERED"


def test_reprocessing_same_observation_is_idempotent():
    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    track_record = InMemoryTrackRecordStore()
    orchestrator = SignalLifecycleOrchestrator(history, alerts, track_record)

    signal = make_signal()
    state = SignalMarketState(
        datetime(2026, 10, 4, tzinfo=timezone.utc), Decimal("110")
    )

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
        SignalMarketState(datetime(2026, 10, 4, tzinfo=timezone.utc), Decimal("90")),
        entry_price=Decimal("100"),
    )

    outcome = track_record.get(result.signal_id)
    assert outcome is not None
    assert outcome.realized_return == Decimal("0.10")
    assert outcome.realized_r == Decimal("2")
