from datetime import date, datetime, time, timezone

import pytest

from app.domain.market_data.session_calendar import (
    CalendarCoverageError,
    CalendarDayStatus,
    EGXCalendarDay,
    EGXSessionCalendar,
)


def calendar(days: tuple[EGXCalendarDay, ...]) -> EGXSessionCalendar:
    return EGXSessionCalendar(
        version="egx-test-v1",
        timezone="Africa/Cairo",
        coverage_start=days[0].session_date,
        coverage_end=days[-1].session_date,
        days=days,
    )


def test_calendar_requires_an_explicit_record_for_every_covered_date() -> None:
    with pytest.raises(ValueError, match="every date"):
        calendar(
            (
                EGXCalendarDay(date(2026, 11, 1), CalendarDayStatus.NON_TRADING),
                EGXCalendarDay(date(2026, 11, 3), CalendarDayStatus.NON_TRADING),
            )
        )


def test_calendar_only_returns_explicitly_closed_sessions() -> None:
    value = calendar(
        (
            EGXCalendarDay(
                date(2026, 11, 1),
                CalendarDayStatus.CLOSED,
                time(10, 0),
                time(14, 30),
                datetime(2026, 11, 1, 14, 31, tzinfo=timezone.utc),
            ),
            EGXCalendarDay(date(2026, 11, 2), CalendarDayStatus.NON_TRADING),
            EGXCalendarDay(
                date(2026, 11, 3),
                CalendarDayStatus.SCHEDULED,
                time(10, 0),
                time(14, 30),
            ),
            EGXCalendarDay(
                date(2026, 11, 4),
                CalendarDayStatus.CLOSED,
                time(10, 0),
                time(13, 30),
                datetime(2026, 11, 4, 14, 0, tzinfo=timezone.utc),
                "Shortened session",
            ),
        )
    )

    completed = value.completed_sessions_between(
        date(2026, 10, 31),
        date(2026, 11, 4),
        as_of=datetime(2026, 11, 4, 15, 0, tzinfo=timezone.utc),
    )

    assert completed == (date(2026, 11, 1), date(2026, 11, 4))
    assert value.unconfirmed_trading_sessions_between(
        date(2026, 10, 31), date(2026, 11, 4)
    ) == (date(2026, 11, 3),)


def test_closed_session_is_not_effective_before_closed_at() -> None:
    value = calendar(
        (
            EGXCalendarDay(
                date(2026, 11, 1),
                CalendarDayStatus.CLOSED,
                time(10, 0),
                time(14, 30),
                datetime(2026, 11, 1, 15, 0, tzinfo=timezone.utc),
            ),
        )
    )

    assert not value.is_completed_session(
        date(2026, 11, 1),
        as_of=datetime(2026, 11, 1, 14, 59, tzinfo=timezone.utc),
    )
    assert value.is_completed_session(
        date(2026, 11, 1),
        as_of=datetime(2026, 11, 1, 15, 0, tzinfo=timezone.utc),
    )


def test_calendar_fails_closed_outside_declared_coverage() -> None:
    value = calendar(
        (EGXCalendarDay(date(2026, 11, 1), CalendarDayStatus.NON_TRADING),)
    )

    with pytest.raises(CalendarCoverageError, match="outside calendar coverage"):
        value.day_for(date(2026, 11, 2))


def test_calendar_rejects_naive_close_confirmation() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        EGXCalendarDay(
            date(2026, 11, 1),
            CalendarDayStatus.CLOSED,
            time(10, 0),
            time(14, 30),
            datetime(2026, 11, 1, 14, 31),
        )


def test_calendar_rejects_non_trading_day_with_session_times() -> None:
    with pytest.raises(ValueError, match="cannot have session times"):
        EGXCalendarDay(
            date(2026, 11, 1),
            CalendarDayStatus.NON_TRADING,
            time(10, 0),
            time(14, 30),
        )


def test_calendar_from_dict_parses_versioned_operator_document() -> None:
    value = EGXSessionCalendar.from_dict(
        {
            "version": "egx-2026-11-v1",
            "timezone": "Africa/Cairo",
            "coverage_start": "2026-11-01",
            "coverage_end": "2026-11-02",
            "days": [
                {"date": "2026-11-01", "status": "NON_TRADING"},
                {
                    "date": "2026-11-02",
                    "status": "CLOSED",
                    "session_open": "10:00",
                    "session_close": "14:30",
                    "closed_at": "2026-11-02T14:31:00+02:00",
                },
            ],
        }
    )

    assert value.version == "egx-2026-11-v1"
    assert value.day_for(date(2026, 11, 2)).status is CalendarDayStatus.CLOSED


@pytest.mark.parametrize(
    ("open_time", "close_time"),
    [(time(14, 30), time(10, 0)), (time(10, 0), time(10, 0))],
)
def test_calendar_rejects_invalid_session_time_order(
    open_time: time, close_time: time
) -> None:
    with pytest.raises(ValueError, match="later than session open"):
        EGXCalendarDay(
            date(2026, 11, 1),
            CalendarDayStatus.SCHEDULED,
            open_time,
            close_time,
        )


def test_calendar_rejects_unknown_timezone() -> None:
    with pytest.raises(ValueError, match="valid IANA timezone"):
        EGXSessionCalendar(
            version="egx-test-v1",
            timezone="Not/A_Timezone",
            coverage_start=date(2026, 11, 1),
            coverage_end=date(2026, 11, 1),
            days=(EGXCalendarDay(date(2026, 11, 1), CalendarDayStatus.NON_TRADING),),
        )


def test_calendar_rejects_close_confirmation_before_configured_close() -> None:
    with pytest.raises(ValueError, match="cannot precede"):
        EGXCalendarDay(
            date(2026, 11, 1),
            CalendarDayStatus.CLOSED,
            time(10, 0),
            time(14, 30),
            datetime(2026, 11, 1, 12, 29, tzinfo=timezone.utc),
        )


def test_calendar_requires_local_wall_clock_session_times() -> None:
    with pytest.raises(ValueError, match="Cairo local wall-clock"):
        EGXCalendarDay(
            date(2026, 11, 1),
            CalendarDayStatus.SCHEDULED,
            time(10, 0, tzinfo=timezone.utc),
            time(14, 30),
        )
