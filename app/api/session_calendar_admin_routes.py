from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID
from sqlite3 import IntegrityError

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.application.market_data.calendar_publication import CalendarPublicationUnitOfWork
from app.application.market_data.calendar_artifact_storage import (
    CalendarArtifactIntegrityError,
    CalendarArtifactService,
    CalendarArtifactStorageNotConfiguredError,
)
from app.application.market_data.session_calendar_store import (
    CalendarActivationEvent,
    SessionCalendarStore,
    StoredCalendarVersion,
)
from app.application.security.identity import AuthenticatedIdentity
from app.domain.market_data.calendar_evidence import CalendarEvidence, CalendarEvidenceKind, CalendarEvidenceSourceClass, CalendarArtifactRetention
from app.domain.market_data.session_calendar import (
    CalendarDayStatus,
    EGXSessionCalendar,
)


class CalendarDayPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    status: CalendarDayStatus
    session_open: time | None = None
    session_close: time | None = None
    closed_at: datetime | None = None
    reason: str | None = Field(default=None, max_length=500)
    exceptional_hours: bool = False


class CalendarEvidencePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: UUID | None = None
    session_date: date
    evidence_kind: CalendarEvidenceKind
    source_type: str = Field(min_length=1, max_length=100)
    source_class: CalendarEvidenceSourceClass
    source_publisher: str = Field(min_length=1, max_length=100)
    market_scope: str = Field(min_length=1, max_length=100)
    effective_from: date
    effective_through: date
    retrieved_at: datetime
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_retention: CalendarArtifactRetention
    artifact_storage_reference: str | None = Field(default=None, max_length=1000)
    artifact_not_retained_reason: str | None = Field(default=None, max_length=500)
    source_reference: str = Field(min_length=1, max_length=1000)
    claim: str = Field(min_length=1, max_length=2000)
    observed_at: datetime
    source_published_at: datetime | None = None
    supersedes_evidence_id: UUID | None = None
    supersession_reason: str | None = Field(default=None, max_length=500)

    @field_validator("source_type", "source_reference", "claim", "source_publisher", "market_scope", mode="before")
    @classmethod
    def strip_evidence_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must be non-empty")
        return normalized


class CalendarPublicationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(
        min_length=1,
        max_length=120,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$",
    )
    timezone: str = Field(min_length=1, max_length=100)
    coverage_start: date
    coverage_end: date
    days: list[CalendarDayPayload] = Field(min_length=1)
    evidence: list[CalendarEvidencePayload] = Field(min_length=1, max_length=2000)
    source_reference: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("version", "timezone", "source_reference", "reason", mode="before")
    @classmethod
    def strip_required_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must be non-empty")
        return normalized


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
                "exceptional_hours": day.exceptional_hours,
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
    publication_uow: CalendarPublicationUnitOfWork | None = None,
    artifact_service: CalendarArtifactService | None = None,
) -> APIRouter:
    router = APIRouter()

    def configured_store() -> SessionCalendarStore:
        if store is None:
            raise HTTPException(
                status_code=503,
                detail="Session calendar management is not configured",
            )
        return store

    def configured_publication_uow() -> CalendarPublicationUnitOfWork:
        if publication_uow is None:
            raise HTTPException(
                status_code=503,
                detail="Evidence-backed atomic calendar publication is not configured",
            )
        return publication_uow

    def configured_artifact_service() -> CalendarArtifactService:
        if artifact_service is None:
            raise HTTPException(
                status_code=503,
                detail="Calendar artifact storage is not configured",
            )
        return artifact_service

    @router.post("/api/v1/owner/session-calendars/artifacts", status_code=201)
    async def upload_calendar_artifact(
        request: Request,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        service = configured_artifact_service()
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/octet-stream":
            raise HTTPException(
                status_code=415,
                detail="Calendar artifacts must be uploaded as application/octet-stream",
            )

        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > service.max_artifact_bytes:
                raise HTTPException(
                    status_code=413,
                    detail="Calendar artifact exceeds the configured size limit",
                )
            content.extend(chunk)

        try:
            receipt = service.archive(bytes(content))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except (CalendarArtifactIntegrityError, OSError) as error:
            raise HTTPException(
                status_code=503,
                detail="Calendar artifact could not be stored and verified",
            ) from error

        return {
            "storage_reference": receipt.storage_reference,
            "artifact_sha256": receipt.sha256,
            "size_bytes": receipt.size_bytes,
            "integrity": "VERIFIED",
        }

    @router.post("/api/v1/owner/session-calendars/versions", status_code=201)
    def publish_calendar_version(
        payload: CalendarPublicationPayload,
        identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        calendar_document = payload.model_dump(
            mode="json",
            exclude={"source_reference", "reason", "evidence"},
        )
        actor = identity.subject.strip()
        if not actor:
            raise HTTPException(
                status_code=403,
                detail="Authenticated operator identity is invalid",
            )
        try:
            actor_id = UUID(actor)
            calendar = EGXSessionCalendar.from_dict(calendar_document)
            evidence = tuple(
                CalendarEvidence.create(
                    calendar_version=calendar.version,
                    session_date=item.session_date,
                    evidence_id=item.evidence_id,
                    evidence_kind=item.evidence_kind,
                    source_type=item.source_type,
                    source_reference=item.source_reference,
                    claim=item.claim,
                    recorded_by=actor_id,
                    observed_at=item.observed_at,
                    source_published_at=item.source_published_at,
                    supersedes_evidence_id=item.supersedes_evidence_id,
                    supersession_reason=item.supersession_reason,
                    source_class=item.source_class,
                    source_publisher=item.source_publisher,
                    market_scope=item.market_scope,
                    effective_from=item.effective_from,
                    effective_through=item.effective_through,
                    retrieved_at=item.retrieved_at,
                    artifact_sha256=item.artifact_sha256,
                    artifact_retention=item.artifact_retention,
                    artifact_storage_reference=item.artifact_storage_reference,
                    artifact_not_retained_reason=item.artifact_not_retained_reason,
                )
                for item in payload.evidence
            )
            stored, stored_evidence = configured_publication_uow().publish(
                calendar,
                evidence,
                published_by=actor,
                source_reference=payload.source_reference,
                reason=payload.reason,
            )
        except CalendarArtifactStorageNotConfiguredError as error:
            raise HTTPException(
                status_code=503,
                detail="Verified calendar artifact storage is not configured",
            ) from error
        except FileNotFoundError as error:
            raise HTTPException(
                status_code=422,
                detail="Archived calendar artifact does not exist in configured storage",
            ) from error
        except CalendarArtifactIntegrityError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except OSError as error:
            raise HTTPException(
                status_code=503,
                detail="Calendar artifact storage is temporarily unavailable",
            ) from error
        except IntegrityError as error:
            raise HTTPException(
                status_code=409,
                detail="Calendar version or evidence record already exists",
            ) from error
        except (ValueError, KeyError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        response = _version_payload(stored, include_calendar=True)
        response["evidence"] = [
            {
                "evidence_id": str(item.evidence_id),
                "session_date": item.session_date.isoformat(),
                "evidence_kind": item.evidence_kind.value,
                "content_sha256": item.content_sha256,
                "artifact_sha256": item.artifact_sha256,
                "source_class": item.source_class.value if item.source_class else None,
                "artifact_retention": item.artifact_retention.value if item.artifact_retention else None,
            }
            for item in stored_evidence
        ]
        return response

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
