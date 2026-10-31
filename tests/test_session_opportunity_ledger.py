from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.reporting.build_session_opportunity_ledger import BuildSessionOpportunityLedger
from app.application.signals.store import InMemorySignalHistoryStore
from app.application.signals.track_record import InMemoryTrackRecordStore
from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord


def dt(hour: int) -> datetime:
    return datetime(2026, 10, 26, hour, tzinfo=timezone.utc)


def make_signal() -> Signal:
    return Signal(
        symbol="EGAL",
        direction=SignalDirection.BUY,
        status=SignalStatus.ACTIVE,
        generated_at=dt(8),
        timeframe="1d",
        entry_zone=PriceZone(Decimal("100"), Decimal("102")),
        invalidation=Decimal("95"),
        targets=(Target(Decimal("110"), "T1"), Target(Decimal("115"), "T2")),
        confidence=Decimal("70"),
        risk_score=Decimal("30"),
        evidence=(SignalEvidence("trend", "Higher highs and higher lows"),),
        strategy_id="trend-breakout",
        strategy_version="1",
        data_timestamp=dt(7),
    )


def test_report_reconstructs_state_as_of_generation_time() -> None:
    history = InMemorySignalHistoryStore()
    track = InMemoryTrackRecordStore()
    signal = make_signal()
    created = history.record(signal, "CREATED", dt(8))
    invalidated = replace(signal, status=SignalStatus.INVALIDATED)
    history.record(invalidated, "STATUS_INVALIDATED", dt(12))
    track.record(SignalOutcomeRecord(
        signal_id=created.signal_id,
        symbol="EGAL",
        outcome=SignalOutcome.INVALIDATED,
        direction=SignalDirection.BUY,
        observed_at=dt(12),
        entry_price=Decimal("101"),
        exit_price=Decimal("95"),
        realized_return=Decimal("-0.0594"),
        realized_r=Decimal("-1"),
        invalidation=Decimal("95"),
        target_label=None,
        strategy_id="trend-breakout",
        strategy_version="1",
        data_timestamp=dt(12),
    ))
    builder = BuildSessionOpportunityLedger(history, track)

    early = builder.execute(date(2026, 10, 26), generated_at=dt(10))
    assert early.total_count == 1
    assert early.opportunities[0].current_status is SignalStatus.ACTIVE
    assert early.opportunities[0].market_proxy_outcome is None
    assert early.opportunities[0].source_data_timestamp == dt(7)
    assert early.opportunities[0].outcome_data_timestamp is None
    assert early.unresolved_count == 1

    final = builder.execute(date(2026, 10, 26), generated_at=dt(13))
    assert final.opportunities[0].current_status is SignalStatus.INVALIDATED
    assert final.opportunities[0].market_proxy_outcome is SignalOutcome.INVALIDATED
    assert final.opportunities[0].market_proxy_return == Decimal("-0.0594")
    assert final.opportunities[0].source_data_timestamp == dt(7)
    assert final.opportunities[0].outcome_data_timestamp == dt(12)
    assert final.resolved_proxy_count == 1
    assert final.unresolved_count == 0
    assert final.opportunities[0].original_targets == (
        ("T1", Decimal("110")), ("T2", Decimal("115"))
    )


def test_report_requires_timezone_aware_generation_time() -> None:
    builder = BuildSessionOpportunityLedger(InMemorySignalHistoryStore(), InMemoryTrackRecordStore())
    with pytest.raises(ValueError, match="timezone-aware"):
        builder.execute(date(2026, 10, 26), generated_at=datetime(2026, 10, 26, 13))


def test_signal_outcome_rejects_naive_observation_timestamp() -> None:
    with pytest.raises(ValueError, match="observed_at.*timezone-aware"):
        SignalOutcomeRecord(
            signal_id=uuid4(),
            symbol="EGAL",
            outcome=SignalOutcome.INVALIDATED,
            direction=SignalDirection.BUY,
            observed_at=datetime(2026, 10, 26, 12),
            entry_price=Decimal("101"),
            exit_price=Decimal("95"),
            realized_return=Decimal("-0.0594"),
            realized_r=Decimal("-1"),
            invalidation=Decimal("95"),
            target_label=None,
            strategy_id="trend-breakout",
            strategy_version="1",
            data_timestamp=datetime(2026, 10, 26, 11, tzinfo=timezone.utc),
        )


def test_report_excludes_signal_generated_after_snapshot_cutoff() -> None:
    history = InMemorySignalHistoryStore()
    future_signal = replace(make_signal(), generated_at=dt(11))
    history.record(future_signal, "CREATED", dt(9))
    builder = BuildSessionOpportunityLedger(history, InMemoryTrackRecordStore())

    report = builder.execute(date(2026, 10, 26), generated_at=dt(10))

    assert report.total_count == 0
    assert report.unresolved_count == 0
