from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class CalendarDayStatus(StrEnum):
    NON_TRADING = "NON_TRADING"
    SCHEDULED = "SCHEDULED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class CalendarCoverageError(ValueError):
    """Raised when a requested date is outside the explicit calendar coverage."""


@dataclass(frozen=True)
class EGXCalendarDay:
    session_date: date
    status: CalendarDayStatus
    session_open: time | None = None
    session_close: time | None = None
    closed_at: datetime | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, CalendarDayStatus):
            raise ValueError("Calendar day status must be a CalendarDayStatus value")
        is_trading = self.status in {
            CalendarDayStatus.SCHEDULED,
            CalendarDayStatus.OPEN,
            CalendarDayStatus.CLOSED,
        }
        if is_trading and (
            self.session_open is None or self.session_close is None
        ):
            raise ValueError("Trading calendar days require explicit open and close times")
        if not is_trading and (
            self.session_open is not None or self.session_close is not None
        ):
            raise ValueError("Non-trading and cancelled days cannot have session times")
        if self.session_open is not None and self.session_open.tzinfo is not None:
            raise ValueError("Session open must be a Cairo local wall-clock time")
        if self.session_close is not None and self.session_close.tzinfo is not None:
            raise ValueError("Session close must be a Cairo local wall-clock time")
        if (
            self.session_open is not None
            and self.session_close is not None
            and self.session_close <= self.session_open
        ):
            raise ValueError("Session close must be later than session open")
        if self.status is CalendarDayStatus.CLOSED:
            if self.closed_at is None:
                raise ValueError("A CLOSED session requires an explicit closed_at timestamp")
            if self.closed_at.tzinfo is None or self.closed_at.utcoffset() is None:
                raise ValueError("closed_at must be timezone-aware")
            cairo_close = self.closed_at.astimezone(ZoneInfo("Africa/Cairo"))
            if cairo_close.date() != self.session_date:
                raise ValueError("closed_at must fall on the session date in Cairo time")
            assert self.session_close is not None
            if cairo_close.timetz().replace(tzinfo=None) < self.session_close:
                raise ValueError("closed_at cannot precede the configured session close")
        elif self.closed_at is not None:
            raise ValueError("closed_at is only valid for a CLOSED session")
        if self.reason is not None and not self.reason.strip():
            raise ValueError("reason must be non-empty when provided")


@dataclass(frozen=True)
class EGXSessionCalendar:
    version: str
    timezone: str
    coverage_start: date
    coverage_end: date
    days: tuple[EGXCalendarDay, ...]

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("Calendar version is required")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Calendar timezone must be a valid IANA timezone") from error
        if self.timezone != "Africa/Cairo":
            raise ValueError("EGX session calendar timezone must be Africa/Cairo")
        if self.coverage_end < self.coverage_start:
            raise ValueError("Calendar coverage end must not precede coverage start")
        expected_day_count = (self.coverage_end - self.coverage_start).days + 1
        if len(self.days) != expected_day_count:
            raise ValueError(
                "Calendar must contain exactly one ordered explicit record for every "
                "date in its declared coverage"
            )
        start_ordinal = self.coverage_start.toordinal()
        if any(
            day.session_date.toordinal() != start_ordinal + offset
            for offset, day in enumerate(self.days)
        ):
            raise ValueError(
                "Calendar must contain exactly one ordered explicit record for every "
                "date in its declared coverage"
            )

    def day_for(self, value: date) -> EGXCalendarDay:
        self._require_coverage(value, value)
        return self.days[(value - self.coverage_start).days]

    def is_completed_session(self, value: date, *, as_of: datetime) -> bool:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        day = self.day_for(value)
        if day.status is not CalendarDayStatus.CLOSED:
            return False
        assert day.closed_at is not None
        return day.closed_at <= as_of.astimezone(ZoneInfo(self.timezone))

    def completed_sessions_between(
        self,
        after_date: date,
        through_date: date,
        *,
        as_of: datetime,
    ) -> tuple[date, ...]:
        if through_date < after_date:
            raise ValueError("through_date must not precede after_date")
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        self._require_exclusive_range_coverage(after_date, through_date)
        return tuple(
            day.session_date
            for day in self.days
            if after_date < day.session_date <= through_date
            and day.status is CalendarDayStatus.CLOSED
            and day.closed_at is not None
            and day.closed_at <= as_of.astimezone(ZoneInfo(self.timezone))
        )

    def unconfirmed_trading_sessions_between(
        self, after_date: date, through_date: date
    ) -> tuple[date, ...]:
        if through_date < after_date:
            raise ValueError("through_date must not precede after_date")
        self._require_exclusive_range_coverage(after_date, through_date)
        return tuple(
            day.session_date
            for day in self.days
            if after_date < day.session_date <= through_date
            and day.status in {
                CalendarDayStatus.SCHEDULED,
                CalendarDayStatus.OPEN,
            }
        )

    def _require_coverage(self, start: date, end: date) -> None:
        if start < self.coverage_start or end > self.coverage_end:
            raise CalendarCoverageError(
                f"Requested range {start.isoformat()}..{end.isoformat()} is outside "
                f"calendar coverage {self.coverage_start.isoformat()}.."
                f"{self.coverage_end.isoformat()}"
            )

    def _require_exclusive_range_coverage(self, after_date: date, through_date: date) -> None:
        # after_date is exclusive. Permit the immediately preceding cursor date,
        # but never silently bridge an actual gap before the declared coverage.
        if after_date < self.coverage_start:
            days_before_coverage = (self.coverage_start - after_date).days
            if days_before_coverage != 1:
                raise CalendarCoverageError(
                    f"Requested range {after_date.isoformat()}..{through_date.isoformat()} "
                    f"starts before calendar coverage {self.coverage_start.isoformat()}.."
                    f"{self.coverage_end.isoformat()}"
                )
        self._require_coverage(max(after_date, self.coverage_start), through_date)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> EGXSessionCalendar:
        try:
            raw_days = payload["days"]
            days = tuple(
                EGXCalendarDay(
                    session_date=date.fromisoformat(item["date"]),
                    status=CalendarDayStatus(item["status"]),
                    session_open=(
                        time.fromisoformat(item["session_open"])
                        if item.get("session_open")
                        else None
                    ),
                    session_close=(
                        time.fromisoformat(item["session_close"])
                        if item.get("session_close")
                        else None
                    ),
                    closed_at=(
                        datetime.fromisoformat(item["closed_at"])
                        if item.get("closed_at")
                        else None
                    ),
                    reason=item.get("reason"),
                )
                for item in raw_days
            )
            return cls(
                version=payload["version"],
                timezone=payload["timezone"],
                coverage_start=date.fromisoformat(payload["coverage_start"]),
                coverage_end=date.fromisoformat(payload["coverage_end"]),
                days=days,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid EGX session calendar: {error}") from error
