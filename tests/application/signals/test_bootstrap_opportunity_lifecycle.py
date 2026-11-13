from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from app.application.alerts.in_memory import InMemoryAlertPublisher
from app.application.market_data.session_calendar_store import StoredCalendarVersion
from app.application.signals.bootstrap_opportunity_lifecycle import BootstrapOpportunityLifecycle
from app.application.signals.lifecycle_unit_of_work import InMemorySignalLifecycleUnitOfWork
from app.application.signals.store import InMemorySignalHistoryStore
from app.application.signals.track_record import InMemoryTrackRecordStore
from app.domain.market_data.session_calendar import (
    CalendarDayStatus,
    EGXCalendarDay,
    EGXSessionCalendar,
)
from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)


CAIRO = ZoneInfo("Africa/Cairo")
START = date(2026, 10, 1)
END = date(2026, 11, 30)


class FakeCalendarStore:
    def __init__(self, calendar_version: StoredCalendarVersion):
        self.calendar_version = calendar_version

    def get_version(self, version: str):
        return self.calendar_version if version == self.calendar_version.version else None


def make_calendar(coverage_end: date = END) -> StoredCalendarVersion:
    days = []
    current = START
    while current <= coverage_end:
        trading = current.weekday() not in (4, 5)
        days.append(
            EGXCalendarDay(
                session_date=current,
                status=CalendarDayStatus.SCHEDULED if trading else CalendarDayStatus.NON_TRADING,
                session_open=time(10, 0) if trading else None,
                session_close=time(14, 30) if trading else None,
            )
        )
        current += timedelta(days=1)
    calendar = EGXSessionCalendar(
        version="calendar-v1",
        timezone="Africa/Cairo",
        coverage_start=START,
        coverage_end=coverage_end,
        days=tuple(days),
    )
    return StoredCalendarVersion(
        version="calendar-v1",
        calendar=calendar,
        sha256="a" * 64,
        published_at=datetime(2026, 9, 30, 12, tzinfo=CAIRO),
        published_by="calendar-operator",
        source_reference="official-calendar-evidence",
        publication_reason="approved calendar fixture",
    )


def make_signal(symbol: str = "COMI") -> Signal:
    generated = datetime(2026, 10, 1, 9, tzinfo=CAIRO)
    return Signal(
        symbol=symbol,
        direction=SignalDirection.BUY,
        status=SignalStatus.ACTIVE,
        generated_at=generated,
        timeframe="DAILY",
        entry_zone=PriceZone(Decimal("99"), Decimal("101")),
        invalidation=Decimal("95"),
        targets=(Target(Decimal("120"), "T1"),),
        confidence=Decimal("80"),
        risk_score=Decimal("20"),
        evidence=(SignalEvidence("trend", "trend evidence"),),
        strategy_id="breakout",
        strategy_version="1",
        data_timestamp=generated,
    )


def build_service():
    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    track_record = InMemoryTrackRecordStore()
    unit_of_work = InMemorySignalLifecycleUnitOfWork(history, alerts, track_record)
    calendar_store = FakeCalendarStore(make_calendar())
    service = BootstrapOpportunityLifecycle(
        history=history,
        calendar_store=calendar_store,
        unit_of_work=unit_of_work,
    )
    return service, history, unit_of_work, calendar_store


def test_bootstrap_derives_exclusive_baseline_from_cairo_publication_time():
    service, history, unit_of_work, _ = build_service()
    signal = make_signal()
    publication_at = datetime(2026, 10, 3, 23, 30, tzinfo=timezone.utc)
    publication = history.record(signal, "PUBLISHED", publication_at)

    result = service.execute(
        calendar_version="calendar-v1",
        operator_id="authenticated-user-7",
        reason="initial lifecycle bootstrap",
        next_evaluation_date=date(2026, 10, 6),
        recorded_at=datetime(2026, 10, 6, 8, tzinfo=CAIRO),
    )

    records = unit_of_work.execute(lambda tx: tx.bootstrap_records(publication.signal_id))
    assert result.status == "BOOTSTRAPPED"
    assert result.opportunity_count == 1
    assert records[0].baseline_date == date(2026, 10, 4)
    assert records[0].publication_recorded_at == publication_at
    assert records[0].operator_id == "authenticated-user-7"


def test_bootstrap_selects_only_latest_active_revision_with_own_baseline():
    service, history, unit_of_work, _ = build_service()
    parent = history.record(
        make_signal(),
        "PUBLISHED",
        datetime(2026, 10, 2, 10, tzinfo=CAIRO),
    )
    child_signal = replace_signal = make_signal()
    child_signal = Signal(
        **{
            **child_signal.__dict__,
            "confidence": Decimal("85"),
        }
    )
    child = history.record_revision(
        child_signal,
        "PUBLISHED_VERSION",
        datetime(2026, 10, 5, 11, tzinfo=CAIRO),
        parent_signal_id=parent.signal_id,
        reason="material setup revision",
    )

    result = service.execute(
        calendar_version="calendar-v1",
        operator_id="authenticated-user-7",
        reason="initial lifecycle bootstrap",
        next_evaluation_date=date(2026, 10, 6),
        recorded_at=datetime(2026, 10, 6, 8, tzinfo=CAIRO),
    )

    parent_records = unit_of_work.execute(lambda tx: tx.bootstrap_records(parent.signal_id))
    child_records = unit_of_work.execute(lambda tx: tx.bootstrap_records(child.signal_id))
    assert result.opportunity_count == 1
    assert parent_records == ()
    assert len(child_records) == 1
    assert child_records[0].baseline_date == date(2026, 10, 5)


def test_bootstrap_retry_is_idempotent_even_with_a_later_request_timestamp():
    service, history, unit_of_work, _ = build_service()
    publication = history.record(
        make_signal(),
        "PUBLISHED",
        datetime(2026, 10, 2, 10, tzinfo=CAIRO),
    )
    first = service.execute(
        calendar_version="calendar-v1",
        operator_id="authenticated-user-7",
        reason="initial lifecycle bootstrap",
        next_evaluation_date=date(2026, 10, 6),
        recorded_at=datetime(2026, 10, 6, 8, tzinfo=CAIRO),
    )
    second = service.execute(
        calendar_version="calendar-v1",
        operator_id="authenticated-user-7",
        reason="initial lifecycle bootstrap",
        next_evaluation_date=date(2026, 10, 6),
        recorded_at=datetime(2026, 10, 6, 9, tzinfo=CAIRO),
    )

    assert first.status == "BOOTSTRAPPED"
    assert second.status == "ALREADY_BOOTSTRAPPED"
    assert len(unit_of_work.execute(lambda tx: tx.bootstrap_records(publication.signal_id))) == 1


def test_bootstrap_fails_closed_when_calendar_does_not_cover_next_evaluation_date():
    service, history, unit_of_work, calendar_store = build_service()
    publication = history.record(
        make_signal(),
        "PUBLISHED",
        datetime(2026, 10, 2, 10, tzinfo=CAIRO),
    )
    calendar_store.calendar_version = make_calendar(date(2026, 10, 5))

    with pytest.raises(ValueError, match="does not explicitly cover"):
        service.execute(
            calendar_version="calendar-v1",
            operator_id="authenticated-user-7",
            reason="initial lifecycle bootstrap",
            next_evaluation_date=date(2026, 10, 6),
            recorded_at=datetime(2026, 10, 6, 8, tzinfo=CAIRO),
        )

    assert unit_of_work.execute(lambda tx: tx.bootstrap_records(publication.signal_id)) == ()


def test_unpublished_active_signal_is_not_bootstrapped():
    service, history, unit_of_work, _ = build_service()
    history.record(
        make_signal(),
        "CREATED",
        datetime(2026, 10, 2, 10, tzinfo=CAIRO),
    )

    result = service.execute(
        calendar_version="calendar-v1",
        operator_id="authenticated-user-7",
        reason="initial lifecycle bootstrap",
        next_evaluation_date=date(2026, 10, 6),
        recorded_at=datetime(2026, 10, 6, 8, tzinfo=CAIRO),
    )

    assert result.status == "NO_ELIGIBLE_ACTIVE_OPPORTUNITIES"
    assert unit_of_work.execute(lambda tx: tx.bootstrap_batches()) == ()
