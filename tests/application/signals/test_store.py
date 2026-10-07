from datetime import datetime, timezone
from decimal import Decimal

from app.application.signals.store import InMemorySignalHistoryStore
from app.domain.signals.model import PriceZone, Signal, SignalDirection, SignalEvidence, SignalStatus, Target


def signal(status=SignalStatus.ACTIVE):
    now = datetime(2026, 10, 4, tzinfo=timezone.utc)
    return Signal(
        symbol="COMI", direction=SignalDirection.BUY, status=status,
        generated_at=now, timeframe="DAILY",
        entry_zone=PriceZone(Decimal("99"), Decimal("101")),
        invalidation=Decimal("95"),
        targets=(Target(Decimal("105"), "T1"),),
        confidence=Decimal("80"), risk_score=Decimal("20"),
        evidence=(SignalEvidence("trend", "uptrend"),),
        strategy_id="breakout-trend", strategy_version="1.0",
        data_timestamp=now,
    )


def test_record_creates_stable_signal_identity_and_history():
    store = InMemorySignalHistoryStore()
    now = datetime(2026, 10, 4, tzinfo=timezone.utc)
    first = store.record(signal(), "CREATED", now)
    second = store.record(signal(SignalStatus.TRIGGERED), "TRIGGERED", now)
    assert first.signal_id == second.signal_id
    assert len(store.history(first.signal_id)) == 2
    assert store.latest("comi").signal.status is SignalStatus.TRIGGERED


def test_unknown_signal_returns_none():
    store = InMemorySignalHistoryStore()
    assert store.latest("COMI") is None


def test_new_signal_generation_gets_new_identity():
    store = InMemorySignalHistoryStore()
    now = datetime(2026, 10, 4, tzinfo=timezone.utc)
    first = store.record(signal(), "CREATED", now)
    later = store.record(
        Signal(
            **{**signal().__dict__, "generated_at": datetime(2026, 10, 5, tzinfo=timezone.utc),
               "data_timestamp": datetime(2026, 10, 5, tzinfo=timezone.utc)}
        ),
        "CREATED",
        now,
    )
    assert first.signal_id != later.signal_id
    assert store.latest("COMI").signal_id == later.signal_id
