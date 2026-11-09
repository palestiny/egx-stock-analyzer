from __future__ import annotations

from datetime import datetime, time
from sqlite3 import IntegrityError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.application.market_data.session_calendar_store import (
    CalendarActivationEvent,
    SessionCalendarStore,
    StoredCalendarVersion,
)
from app.application.security.identity import AuthenticatedIdentity
from app.domain.market_data.session_calendar import (
    CalendarDayStatus,
    EGXSessionCalendar,
)


class CalendarDayPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str = Field(min_length=10, max_length=10)
    status: CalendarDayStatus
    session_open: time | None = None
    session_close: time | None = None
    closed_at: datetime | None = None
    reason: str | None = Field(default=None, max_length=500)


class CalendarPublicationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1, max_length=120)
    timezone: str = Field(min_length=1, max_length=100)
    coverage_start: str = Field(min_length=10, max_length=10)
    coverage_end: str = Field(min_length=10, max_length=10)
    days: list[CalendarDayPayload] = Field(min_length=1, max_length=800)
    source_reference: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=500)


def _calendar_payload(calendar: EGXSessionCalendar) -> dict[str, object]:
    return {
        "version": calendar.version,
        "timezone": calendar.timezone,
        "coverage_start": calendar.coverage_start.isoformat(),
        "coverage_end": calendar.coverage_end.isoformat(),
        "days": [
            {
                "date": day.session_date.isoformat(),
                "status": day.status.value,
                "session_open": day.session_open.isoformat() if day.session_open else None,
                "session_close": day.session_close.isoformat() if day.session_close else None,
                "closed_at": day.closed_at.isoformat() if day.closed_at else None,
                "reason": day.reason,
            }
            for day in calendar.days
        ],
    }


def _version_payload(
    stored: StoredCalendarVersion,
    *,
    include_calendar: bool,
) -> dict[str, object]:
    result: dict[str, object] = {
        "version": stored.version,
        "sha256": stored.sha256,
        "published_at": stored.published_at.isoformat(),
        "published_by": stored.published_by,
        "source_reference": stored.source_reference,
        "publication_reason": stored.publication_reason,
        "coverage_start": stored.calendar.coverage_start.isoformat(),
        "coverage_end": stored.calendar.coverage_end.isoformat(),
        "timezone": stored.calendar.timezone,
    }
    if include_calendar:
        result["calendar"] = _calendar_payload(stored.calendar)
    return result


def _activation_event_payload(event: CalendarActivationEvent) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "action": event.action,
        "previous_version": event.previous_version,
        "target_version": event.target_version,
        "occurred_at": event.occurred_at.isoformat(),
        "performed_by": event.performed_by,
        "reason": event.reason,
    }


def create_session_calendar_admin_router(
    *,
    store: SessionCalendarStore | None,
    require_operator,
) -> APIRouter:
    router = APIRouter()

    def configured_store() -> SessionCalendarStore:
        if store is None:
            raise HTTPException(
                status_code=503,
                detail="Session calendar management is not configured",
            )
        return store

    @router.post("/api/v1/owner/session-calendars/versions", status_code=201)
    def publish_calendar_version(
        payload: CalendarPublicationPayload,
        identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        calendar_document = payload.model_dump(
            mode="json",
            exclude={"source_reference", "reason"},
        )
        try:
            calendar = EGXSessionCalendar.from_dict(calendar_document)
            stored = configured_store().publish(
                calendar,
                published_by=identity.subject.strip() or "operator",
                source_reference=payload.source_reference,
                reason=payload.reason,
            )
        except IntegrityError as error:
            raise HTTPException(
                status_code=409,
                detail="Calendar version already exists",
            ) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _version_payload(stored, include_calendar=True)

    @router.get("/api/v1/owner/session-calendars/versions")
    def list_calendar_versions(
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        versions = configured_store().list_versions()
        return {
            "items": [
                _version_payload(version, include_calendar=False)
                for version in versions
            ]
        }

    @router.get("/api/v1/owner/session-calendars/versions/{version}")
    def get_calendar_version(
        version: str,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        stored = configured_store().get_version(version)
        if stored is None:
            raise HTTPException(status_code=404, detail="Calendar version not found")
        return _version_payload(stored, include_calendar=True)

    @router.get("/api/v1/owner/session-calendars/active")
    def get_active_calendar(
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        stored = configured_store().get_active()
        if stored is None:
            raise HTTPException(status_code=404, detail="No active session calendar")
        return _version_payload(stored, include_calendar=True)

    @router.get("/api/v1/owner/session-calendars/activation-events")
    def list_calendar_activation_events(
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        events = configured_store().list_activation_events()
        return {"items": [_activation_event_payload(event) for event in events]}

    return router
