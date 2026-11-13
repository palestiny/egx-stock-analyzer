from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.application.market_data.session_calendar_store import StoredCalendarVersion
from app.application.signals.calendar_backed_lifecycle_evaluation_schedule import (
    CalendarBackedLifecycleEvaluationSchedule,
)
from app.domain.market_data.session_calendar import (
    CalendarDayStatus,
    EGXCalendarDay,
    EGXSessionCalendar,
)


CAIRO = ZoneInfo("Africa/Cairo")


class FakeCalendarStore:
    def __init__(self, versions, active_version=None):
        self.versions = versions
        self.active_version = active_version

    def get_version(self, version):
        return self.versions.get(version)

    def get_active(self):
        if self.active_version is None:
            return None
        return self.versions.get(self.active_version)


def stored_calendar(version, statuses):
    start = min(statuses)
    end = max(statuses)
    days = []
    current = start
    while current <= end:
        status = statuses.get(current, CalendarDayStatus.NON_TRADING)
        trading = status in {
            CalendarDayStatus.SCHEDULED,
            CalendarDayStatus.OPEN,
            CalendarDayStatus.CLOSED,
        }
        days.append(EGXCalendarDay(
            session_date=current,
            status=status,
            session_open=time(10) if trading else None,
            session_close=time(14, 30) if trading else None,
            closed_at=(
                datetime.combine(current, time(14, 35), tzinfo=CAIRO)
                if status is CalendarDayStatus.CLOSED else None
            ),
        ))
        current += timedelta(days=1)
    calendar = EGXSessionCalendar(
        version, "Africa/Cairo", start, end, tuple(days)
    )
    return StoredCalendarVersion(
        version, calendar, "a" * 64,
        datetime(2026, 1, 1, tzinfo=CAIRO),
        "operator", "published-source", "schedule fixture",
    )


def test_initial_activation_uses_candidate_calendar_schedule():
    candidate = stored_calendar("candidate", {
        date(2026, 11, 13): CalendarDayStatus.NON_TRADING,
        date(2026, 11, 15): CalendarDayStatus.SCHEDULED,
        date(2026, 11, 16): CalendarDayStatus.SCHEDULED,
    })
    store = FakeCalendarStore({"candidate": candidate})
    schedule = CalendarBackedLifecycleEvaluationSchedule(
        calendar_store=store,
        candidate_calendar_version="candidate",
    )

    assert schedule.next_evaluation_date(after=date(2026, 11, 13)) == date(2026, 11, 15)


def test_calendar_change_and_rollback_use_current_active_calendar_schedule():
    active = stored_calendar("active", {
        date(2026, 11, 13): CalendarDayStatus.NON_TRADING,
        date(2026, 11, 16): CalendarDayStatus.SCHEDULED,
    })
    candidate = stored_calendar("candidate", {
        date(2026, 11, 13): CalendarDayStatus.NON_TRADING,
        date(2026, 11, 17): CalendarDayStatus.SCHEDULED,
    })
    store = FakeCalendarStore(
        {"active": active, "candidate": candidate},
        active_version="active",
    )
    schedule = CalendarBackedLifecycleEvaluationSchedule(
        calendar_store=store,
        candidate_calendar_version="candidate",
    )

    assert schedule.next_evaluation_date(after=date(2026, 11, 13)) == date(2026, 11, 16)


def test_active_calendar_without_future_schedule_fails_closed_without_candidate_fallback():
    active = stored_calendar("active", {
        date(2026, 11, 13): CalendarDayStatus.NON_TRADING,
        date(2026, 11, 16): CalendarDayStatus.CANCELLED,
    })
    candidate = stored_calendar("candidate", {
        date(2026, 11, 13): CalendarDayStatus.NON_TRADING,
        date(2026, 11, 17): CalendarDayStatus.SCHEDULED,
    })
    store = FakeCalendarStore(
        {"active": active, "candidate": candidate},
        active_version="active",
    )
    schedule = CalendarBackedLifecycleEvaluationSchedule(
        calendar_store=store,
        candidate_calendar_version="candidate",
    )

    assert schedule.next_evaluation_date(after=date(2026, 11, 13)) is None


def test_missing_candidate_calendar_fails_closed_on_initial_activation():
    schedule = CalendarBackedLifecycleEvaluationSchedule(
        calendar_store=FakeCalendarStore({}),
        candidate_calendar_version="candidate",
    )

    assert schedule.next_evaluation_date(after=date(2026, 11, 13)) is None
