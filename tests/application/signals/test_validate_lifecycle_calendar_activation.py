from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.application.alerts.in_memory import InMemoryAlertPublisher
from app.application.market_data.session_calendar_store import StoredCalendarVersion
from app.application.signals.bootstrap_opportunity_lifecycle import BootstrapOpportunityLifecycle
from app.application.signals.lifecycle_unit_of_work import (
    InMemorySignalLifecycleUnitOfWork,
    LifecycleObservationRecord,
)
from app.application.signals.store import InMemorySignalHistoryStore
from app.application.signals.track_record import InMemoryTrackRecordStore
from app.application.signals.validate_lifecycle_calendar_activation import (
    ValidateLifecycleCalendarActivation,
)
from app.domain.market_data.session_calendar import (
    CalendarDayStatus, EGXCalendarDay, EGXSessionCalendar,
)
from app.domain.signals.lifecycle import CompletedDailyBarObservation
from app.domain.signals.model import (
    PriceZone, Signal, SignalDirection, SignalEvidence, SignalStatus, Target,
)


CAIRO = ZoneInfo("Africa/Cairo")
START = date(2026, 10, 1)
END = date(2026, 10, 15)


class FakeCalendarStore:
    def __init__(self, stored):
        self.stored = stored

    def get_version(self, version):
        return self.stored if self.stored.version == version else None


class FakeSchedule:
    def __init__(self, next_date):
        self.next_date = next_date
        self.received_after = None

    def next_evaluation_date(self, *, after):
        self.received_after = after
        return self.next_date


def make_calendar(*, version="calendar-v1", end=END, next_status=CalendarDayStatus.SCHEDULED, closed_dates=()):
    days = []
    current = START
    while current <= end:
        trading = current.weekday() not in (4, 5)
        status = CalendarDayStatus.SCHEDULED if trading else CalendarDayStatus.NON_TRADING
        if current in closed_dates:
            status = CalendarDayStatus.CLOSED
        elif current == date(2026, 10, 6):
            status = next_status
        days.append(EGXCalendarDay(
            current, status,
            session_open=time(10, 0) if status in {CalendarDayStatus.SCHEDULED, CalendarDayStatus.CLOSED} else None,
            session_close=time(14, 30) if status in {CalendarDayStatus.SCHEDULED, CalendarDayStatus.CLOSED} else None,
            closed_at=(
                datetime.combine(current, time(14, 35), tzinfo=CAIRO)
                if status is CalendarDayStatus.CLOSED else None
            ),
        ))
        current += timedelta(days=1)
    calendar = EGXSessionCalendar(
        version, "Africa/Cairo", START, end, tuple(days)
    )
    return StoredCalendarVersion(
        version, calendar, "a" * 64,
        datetime(2026, 9, 30, 12, tzinfo=CAIRO),
        "calendar-operator", "official-calendar-evidence", "approved fixture",
    )


def make_signal():
    generated = datetime(2026, 10, 1, 9, tzinfo=CAIRO)
    return Signal(
        symbol="COMI", direction=SignalDirection.BUY, status=SignalStatus.ACTIVE,
        generated_at=generated, timeframe="DAILY",
        entry_zone=PriceZone(Decimal("99"), Decimal("101")),
        invalidation=Decimal("95"), targets=(Target(Decimal("120"), "T1"),),
        confidence=Decimal("80"), risk_score=Decimal("20"),
        evidence=(SignalEvidence("trend", "trend evidence"),),
        strategy_id="breakout", strategy_version="1", data_timestamp=generated,
    )


def setup(*, bootstrap=True, next_date=date(2026, 10, 6), bootstrap_next_date=None, end=END, next_status=CalendarDayStatus.SCHEDULED, version="calendar-v1", closed_dates=()):
    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    track = InMemoryTrackRecordStore()
    uow = InMemorySignalLifecycleUnitOfWork(history, alerts, track)
    stored = make_calendar(version=version, end=end, next_status=next_status, closed_dates=closed_dates)
    calendar_store = FakeCalendarStore(stored)
    publication = history.record(
        make_signal(), "PUBLISHED", datetime(2026, 10, 2, 10, tzinfo=CAIRO)
    )
    if bootstrap:
        BootstrapOpportunityLifecycle(
            history=history, calendar_store=calendar_store, unit_of_work=uow
        ).execute(
            calendar_version=stored.version,
            operator_id="operator-1",
            reason="bootstrap before activation",
            next_evaluation_date=bootstrap_next_date or next_date,
            recorded_at=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
        )
    schedule = FakeSchedule(next_date)
    validator = ValidateLifecycleCalendarActivation(
        history=history, calendar_store=calendar_store,
        unit_of_work=uow, schedule=schedule,
    )
    return validator, schedule, publication, uow


def test_calendar_activation_validation_accepts_complete_bootstrap_and_explicit_coverage():
    validator, schedule, _, _ = setup()
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is True
    assert result.checked_opportunity_count == 1
    assert result.blockers == ()
    assert schedule.received_after == date(2026, 10, 5)


def test_calendar_activation_validation_rejects_missing_bootstrap():
    validator, _, _, _ = setup(bootstrap=False)
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert result.blockers[0].code == "BOOTSTRAP_MISSING_OR_AMBIGUOUS"


def test_calendar_activation_validation_rejects_incomplete_candidate_coverage():
    validator, _, _, _ = setup(end=date(2026, 10, 5), bootstrap_next_date=date(2026, 10, 5))
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert any(item.code == "CALENDAR_COVERAGE_INCOMPLETE" for item in result.blockers)


def test_calendar_activation_validation_rejects_non_trading_next_evaluation_date():
    validator, _, _, _ = setup(next_status=CalendarDayStatus.NON_TRADING, bootstrap_next_date=date(2026, 10, 5))
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert any(item.code == "NEXT_EVALUATION_NOT_SCHEDULED" for item in result.blockers)


def test_calendar_activation_validation_fails_closed_without_trusted_schedule_date():
    validator, schedule, _, _ = setup()
    schedule.next_date = None
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert result.blockers[0].code == "NEXT_EVALUATION_DATE_UNAVAILABLE"



def test_calendar_activation_validation_rejects_schedule_date_not_after_today():
    validator, schedule, _, _ = setup(next_date=date(2026, 10, 5))
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert any(item.code == "NEXT_EVALUATION_DATE_NOT_FUTURE" for item in result.blockers)
    assert schedule.received_after == date(2026, 10, 5)



def make_bar(session_date):
    return CompletedDailyBarObservation(
        symbol="COMI",
        provider="attested-provider",
        timeframe="DAILY",
        candle_at=datetime.combine(session_date, time(14, 30), tzinfo=CAIRO),
        observed_at=datetime.combine(session_date, time(15, 40), tzinfo=CAIRO),
        revision="r1",
        source_reference=f"https://provider.example/COMI/{session_date.isoformat()}",
        finality_attestation="provider-finality-v1",
        is_final=True,
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("98"),
        close=Decimal("102"),
    )


def record_cursor(uow, publication, session_date):
    uow.execute(lambda transaction: transaction.record_observation(
        LifecycleObservationRecord(
            signal_id=publication.signal_id,
            bar=make_bar(session_date),
            policy_version="lifecycle-policy-v1",
            calendar_version="calendar-v1",
            resulting_status=SignalStatus.ACTIVE,
        )
    ))


def test_calendar_activation_validation_requires_reconciled_cursor_to_be_closed():
    validator, _, publication, uow = setup()
    record_cursor(uow, publication, date(2026, 10, 5))
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert any(item.code == "RECONCILED_CURSOR_NOT_CLOSED_IN_CANDIDATE" for item in result.blockers)


def test_calendar_activation_validation_accepts_closed_reconciled_cursor():
    validator, _, publication, uow = setup(closed_dates={date(2026, 10, 5)})
    record_cursor(uow, publication, date(2026, 10, 5))
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is True
    assert result.blockers == ()


def test_rollback_candidate_is_revalidated_against_latest_reconciled_cursor():
    validator, _, publication, uow = setup(
        version="calendar-v2",
        closed_dates={date(2026, 10, 5)},
    )
    record_cursor(uow, publication, date(2026, 10, 5))
    # Revalidation happens at rollback time, using the cursor currently persisted,
    # not a previously cached validation result.
    result = validator.execute(
        calendar_version="calendar-v2",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is True
    assert result.checked_opportunity_count == 1
