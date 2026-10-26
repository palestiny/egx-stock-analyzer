from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord
from app.infrastructure.persistence.sqlite_signal_history_store import (
    SQLiteSignalHistoryStore,
)
from app.infrastructure.persistence.sqlite_track_record_store import (
    SQLiteTrackRecordStore,
)


NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def make_signal(
    *,
    status: SignalStatus = SignalStatus.ACTIVE,
    generated_at: datetime = NOW,
) -> Signal:
    return Signal(
        symbol="COMI",
        direction=SignalDirection.BUY,
        status=status,
        generated_at=generated_at,
        timeframe="DAILY",
        entry_zone=PriceZone(Decimal("99"), Decimal("101")),
        invalidation=Decimal("95"),
        targets=(Target(Decimal("105"), "T1"), Target(Decimal("110"), "T2")),
        confidence=Decimal("80"),
        risk_score=Decimal("20"),
        evidence=(
            SignalEvidence("trend", "Uptrend confirmed"),
            SignalEvidence("volume", "Volume above average", Decimal("0.5")),
        ),
        strategy_id="breakout-trend",
        strategy_version="1.0",
        data_timestamp=generated_at,
    )


def make_outcome(signal_id=None) -> SignalOutcomeRecord:
    return SignalOutcomeRecord(
        signal_id=signal_id or uuid4(),
        symbol="COMI",
        outcome=SignalOutcome.TARGET_HIT,
        direction=SignalDirection.BUY,
        observed_at=NOW + timedelta(days=1),
        entry_price=Decimal("100"),
        exit_price=Decimal("105"),
        realized_return=Decimal("0.05"),
        realized_r=Decimal("1.25"),
        invalidation=Decimal("96"),
        target_label="T1",
        strategy_id="breakout-trend",
        strategy_version="1.0",
        data_timestamp=NOW,
    )


def test_sqlite_signal_history_round_trip_and_stable_identity(tmp_path) -> None:
    database = tmp_path / "signals.db"
    store = SQLiteSignalHistoryStore(database)
    signal = make_signal()

    first = store.record(signal, "CREATED", NOW)
    second = store.record(signal, "CREATED", NOW)
    reloaded = SQLiteSignalHistoryStore(database)

    assert first.signal_id == second.signal_id
    assert reloaded.get(first.signal_id) == first
    assert reloaded.history(first.signal_id) == (first,)
    assert reloaded.latest(" comi ") == first


def test_sqlite_signal_history_appends_status_and_is_restart_safe(tmp_path) -> None:
    database = tmp_path / "signals.db"
    store = SQLiteSignalHistoryStore(database)
    created = store.record(make_signal(), "CREATED", NOW)
    triggered = store.record(
        make_signal(status=SignalStatus.TRIGGERED),
        "STATUS_TRIGGERED",
        NOW + timedelta(minutes=1),
    )
    reopened = SQLiteSignalHistoryStore(database)

    history = reopened.history(created.signal_id)
    assert len(history) == 2
    assert history[0] == created
    assert history[1] == triggered
    assert reopened.get(created.signal_id) == triggered
    assert reopened.latest("COMI") == triggered


def test_sqlite_signal_history_rejects_conflicting_replay(tmp_path) -> None:
    store = SQLiteSignalHistoryStore(tmp_path / "signals.db")
    signal = make_signal()
    store.record(signal, "CREATED", NOW)
    changed = Signal(
        **{
            **signal.__dict__,
            "confidence": Decimal("81"),
        }
    )

    with pytest.raises(ValueError, match="different signal event already recorded"):
        store.record(changed, "CREATED", NOW)


def test_sqlite_signal_history_new_generation_gets_new_identity(tmp_path) -> None:
    store = SQLiteSignalHistoryStore(tmp_path / "signals.db")
    first = store.record(make_signal(), "CREATED", NOW)
    next_generated_at = NOW + timedelta(days=1)
    second = store.record(
        make_signal(generated_at=next_generated_at),
        "CREATED",
        next_generated_at,
    )

    assert first.signal_id != second.signal_id
    assert store.latest("COMI") == second


def test_sqlite_signal_history_requires_aware_recorded_at(tmp_path) -> None:
    store = SQLiteSignalHistoryStore(tmp_path / "signals.db")

    with pytest.raises(ValueError, match="recorded_at must be timezone-aware"):
        store.record(make_signal(), "CREATED", datetime(2026, 10, 26, 12, 0))


def test_sqlite_track_record_is_idempotent_and_restart_safe(tmp_path) -> None:
    database = tmp_path / "signals.db"
    store = SQLiteTrackRecordStore(database)
    outcome = make_outcome()

    store.record(outcome)
    store.record(outcome)
    reopened = SQLiteTrackRecordStore(database)

    assert reopened.get(outcome.signal_id) == outcome
    assert reopened.all() == (outcome,)


def test_sqlite_track_record_rejects_conflicting_outcome_for_same_signal(tmp_path) -> None:
    store = SQLiteTrackRecordStore(tmp_path / "signals.db")
    outcome = make_outcome()
    store.record(outcome)
    changed = SignalOutcomeRecord(
        **{
            **outcome.__dict__,
            "realized_r": Decimal("2"),
        }
    )

    with pytest.raises(ValueError, match="different outcome already recorded"):
        store.record(changed)


def test_sqlite_track_record_orders_outcomes_deterministically(tmp_path) -> None:
    store = SQLiteTrackRecordStore(tmp_path / "signals.db")
    later = make_outcome()
    earlier = SignalOutcomeRecord(
        **{
            **make_outcome().__dict__,
            "signal_id": uuid4(),
            "observed_at": NOW,
            "data_timestamp": NOW - timedelta(days=1),
        }
    )
    store.record(later)
    store.record(earlier)

    assert store.all() == (earlier, later)
