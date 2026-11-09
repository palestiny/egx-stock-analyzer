from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.market_data.session_calendar import EGXSessionCalendar


@dataclass(frozen=True)
class StoredCalendarVersion:
    version: str
    calendar: EGXSessionCalendar
    sha256: str
    published_at: datetime
    published_by: str
    source_reference: str
    publication_reason: str


@dataclass(frozen=True)
class CalendarActivationEvent:
    event_id: int
    action: str
    previous_version: str | None
    target_version: str | None
    occurred_at: datetime
    performed_by: str
    reason: str


class SessionCalendarStore(Protocol):
    def publish(
        self,
        calendar: EGXSessionCalendar,
        *,
        published_by: str,
        source_reference: str,
        reason: str,
        published_at: datetime | None = None,
    ) -> StoredCalendarVersion: ...

    def get_version(self, version: str) -> StoredCalendarVersion | None: ...

    def list_versions(self) -> tuple[StoredCalendarVersion, ...]: ...

    def get_active(self) -> StoredCalendarVersion | None: ...

    def list_activation_events(self) -> tuple[CalendarActivationEvent, ...]: ...
