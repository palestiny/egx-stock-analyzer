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
    confidence: Decimal = Decimal("80"),
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
        confidence=confidence,
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



def test_sqlite_signal_history_all_records_returns_full_append_only_timeline(tmp_path) -> None:
    store = SQLiteSignalHistoryStore(tmp_path / "signals.db")
    created = store.record(make_signal(), "CREATED", NOW)
    updated = store.record(
        make_signal(status=SignalStatus.INVALIDATED),
        "STATUS_INVALIDATED",
        NOW + timedelta(minutes=2),
    )
    assert store.all_records() == (created, updated)


def test_sqlite_signal_history_creates_linked_immutable_revision(tmp_path) -> None:
    store = SQLiteSignalHistoryStore(tmp_path / "signal-revisions.db")
    original_signal = make_signal()
    original = store.record(original_signal, "PUBLISHED", NOW)
    revised_signal = Signal(
        **{
            **original_signal.__dict__,
            "targets": (Target(Decimal("108"), "T1"), Target(Decimal("112"), "T2")),
            "evidence": (SignalEvidence("trend", "revised trend confirmation"),),
        }
    )

    revision = store.record_revision(
        revised_signal,
        "PUBLISHED_VERSION",
        NOW + timedelta(minutes=5),
        parent_signal_id=original.signal_id,
        reason="Material target and evidence change",
    )

    link = store.revision_link(revision.signal_id)
    assert revision.signal_id != original.signal_id
    assert link is not None
    assert link.parent_signal_id == original.signal_id
    assert link.revision_number == 2
    assert link.reason == "Material target and evidence change"
    assert store.history(original.signal_id) == (original,)
    assert store.history(revision.signal_id) == (revision,)
    assert store.latest("COMI") == revision
    assert store.latest_for_identity("COMI", "breakout-trend", "1.0", NOW) == revision

    triggered = Signal(**{**revised_signal.__dict__, "status": SignalStatus.TRIGGERED})
    status_record = store.record_for_signal(
        revision.signal_id,
        triggered,
        "STATUS_TRIGGERED",
        NOW + timedelta(minutes=10),
    )
    assert store.get(revision.signal_id) == status_record
    assert store.get(original.signal_id) == original


def test_sqlite_signal_history_does_not_revise_terminal_opportunity(tmp_path) -> None:
    store = SQLiteSignalHistoryStore(tmp_path / "terminal-signal-revision.db")
    terminal = store.record(
        make_signal(status=SignalStatus.TRIGGERED),
        "PUBLISHED",
        NOW,
    )
    with pytest.raises(ValueError, match="terminal opportunities cannot be revised"):
        store.record_revision(
            make_signal(),
            "PUBLISHED_VERSION",
            NOW + timedelta(minutes=5),
            parent_signal_id=terminal.signal_id,
            reason="Attempted terminal rewrite",
        )


def test_sqlite_signal_revision_links_are_append_only(tmp_path) -> None:
    import sqlite3

    database = tmp_path / "append-only-signal-revision.db"
    store = SQLiteSignalHistoryStore(database)
    original = store.record(make_signal(), "PUBLISHED", NOW)
    revision = store.record_revision(
        make_signal(confidence=Decimal("81")),
        "PUBLISHED_VERSION",
        NOW + timedelta(minutes=5),
        parent_signal_id=original.signal_id,
        reason="Confidence changed",
    )
    connection = sqlite3.connect(str(database))
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM signal_revision_links WHERE signal_id = ?",
                (str(revision.signal_id),),
            )
    finally:
        connection.close()



def test_sqlite_active_published_projection_scales_on_disk_and_survives_reopen(tmp_path, monkeypatch) -> None:
    database = tmp_path / "active-opportunity-projection.db"
    store = SQLiteSignalHistoryStore(database)
    expected_active_revisions = 0

    # Exercise a disk-backed SQLite file with active, terminal, and superseded
    # opportunity identities. Revisions retain their own publication event.
    for index in range(240):
        generated_at = NOW + timedelta(minutes=index)
        terminal = index % 5 == 0
        original_signal = make_signal(
            status=SignalStatus.TRIGGERED if terminal else SignalStatus.ACTIVE,
            generated_at=generated_at,
        )
        original = store.record(original_signal, "PUBLISHED", generated_at)

        if terminal:
            continue
        if index % 10 == 1:
            revised_signal = Signal(
                **{
                    **original_signal.__dict__,
                    "targets": (
                        Target(Decimal("108"), "T1"),
                        Target(Decimal("112"), "T2"),
                    ),
                }
            )
            store.record_revision(
                revised_signal,
                "PUBLISHED_VERSION",
                generated_at + timedelta(minutes=1),
                parent_signal_id=original.signal_id,
                reason="Projection regression fixture revision",
            )
        expected_active_revisions += 1

    reopened = SQLiteSignalHistoryStore(database)
    deserialize_calls = 0
    original_deserialize = SQLiteSignalHistoryStore._deserialize_signal

    def count_deserialization(payload: str) -> Signal:
        nonlocal deserialize_calls
        deserialize_calls += 1
        return original_deserialize(payload)

    monkeypatch.setattr(
        SQLiteSignalHistoryStore,
        "_deserialize_signal",
        staticmethod(count_deserialization),
    )
    projected = reopened.latest_active_published_opportunities()

    assert len(projected) == expected_active_revisions
    assert deserialize_calls == expected_active_revisions
    assert all(item.latest.signal.status is SignalStatus.ACTIVE for item in projected)
    assert all(
        item.publication.event in {"PUBLISHED", "PUBLISHED_VERSION"}
        for item in projected
    )
    assert len({item.latest.signal_id for item in projected}) == len(projected)
    assert [str(item.latest.signal_id) for item in projected] == sorted(
        str(item.latest.signal_id) for item in projected
    )
