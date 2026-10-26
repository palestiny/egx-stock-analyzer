from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.application.alerts.publish_signal_opportunity import PublishSignalOpportunity
from app.application.signals.store import InMemorySignalHistoryStore
from app.domain.alerts.model import AlertEventType
from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)
from app.infrastructure.notifications.sqlite_alert_outbox import SQLiteAlertOutbox


NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def make_signal(
    *,
    evidence: str = "Rejected support",
    status: SignalStatus = SignalStatus.ACTIVE,
) -> Signal:
    return Signal(
        symbol="COMI",
        direction=SignalDirection.BUY,
        status=status,
        generated_at=NOW,
        timeframe="1d",
        entry_zone=PriceZone(Decimal("80"), Decimal("81")),
        invalidation=Decimal("78"),
        targets=(Target(Decimal("85"), "T1"),),
        confidence=Decimal("80"),
        risk_score=Decimal("20"),
        evidence=(SignalEvidence("support_rejection", evidence),),
        strategy_id="price-action",
        strategy_version="1",
        data_timestamp=NOW,
    )


def test_publish_signal_opportunity_is_idempotent_and_snapshots_terms(tmp_path) -> None:
    history = InMemorySignalHistoryStore()
    outbox = SQLiteAlertOutbox(tmp_path / "outbox.db")
    publish = PublishSignalOpportunity(history=history, outbox=outbox)
    signal = make_signal()

    first = publish.execute(signal, recorded_at=NOW)
    replay = publish.execute(signal, recorded_at=NOW + timedelta(minutes=1))

    assert first is not None
    assert first.queued_new_event is True
    assert replay is not None
    assert replay.signal_id == first.signal_id
    assert replay.event_id == first.event_id
    assert replay.queued_new_event is False
    assert len(history.history(first.signal_id)) == 1

    event = outbox.get(first.event_id)
    assert event is not None
    assert event.event.event_type is AlertEventType.SIGNAL_PUBLISHED
    assert event.event.signal_snapshot is not None
    assert event.event.signal_snapshot.entry_lower == Decimal("80")
    assert event.event.signal_snapshot.targets[0].price == Decimal("85")


def test_changed_signal_evidence_creates_a_new_publication_event(tmp_path) -> None:
    history = InMemorySignalHistoryStore()
    outbox = SQLiteAlertOutbox(tmp_path / "outbox.db")
    publish = PublishSignalOpportunity(history=history, outbox=outbox)
    first = publish.execute(make_signal(), recorded_at=NOW)
    revised = publish.execute(
        make_signal(evidence="Support evidence revised"),
        recorded_at=NOW + timedelta(minutes=1),
    )

    assert first is not None
    assert revised is not None
    assert revised.signal_id == first.signal_id
    assert revised.event_id != first.event_id
    assert revised.queued_new_event is True
    assert history.history(first.signal_id)[-1].event == "PUBLISHED_VERSION"
    assert len(outbox.pending()) == 2


def test_publish_does_not_reopen_terminal_signal_identity(tmp_path) -> None:
    history = InMemorySignalHistoryStore()
    outbox = SQLiteAlertOutbox(tmp_path / "outbox.db")
    publish = PublishSignalOpportunity(history=history, outbox=outbox)
    first = publish.execute(make_signal(), recorded_at=NOW)
    assert first is not None
    history.record(
        replace(make_signal(), status=SignalStatus.INVALIDATED),
        "STATUS_INVALIDATED",
        NOW + timedelta(minutes=1),
    )

    assert publish.execute(
        make_signal(),
        recorded_at=NOW + timedelta(minutes=2),
    ) is None
    assert len(outbox.pending()) == 1


def test_only_active_signals_can_be_published(tmp_path) -> None:
    publish = PublishSignalOpportunity(
        history=InMemorySignalHistoryStore(),
        outbox=SQLiteAlertOutbox(tmp_path / "outbox.db"),
    )

    with pytest.raises(ValueError, match="only active signals"):
        publish.execute(
            make_signal(status=SignalStatus.INVALIDATED),
            recorded_at=NOW,
        )
