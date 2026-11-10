from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence

from app.application.market_data.session_calendar_store import StoredCalendarVersion
from app.domain.market_data.calendar_evidence import CalendarEvidence
from app.domain.market_data.session_calendar import EGXSessionCalendar


class CalendarPublicationUnitOfWork(Protocol):
    """Atomic persistence boundary for an immutable calendar and its day evidence."""

    def publish(
        self,
        calendar: EGXSessionCalendar,
        evidence: Sequence[CalendarEvidence],
        *,
        published_by: str,
        source_reference: str,
        reason: str,
        published_at: datetime | None = None,
    ) -> tuple[StoredCalendarVersion, tuple[CalendarEvidence, ...]]: ...
