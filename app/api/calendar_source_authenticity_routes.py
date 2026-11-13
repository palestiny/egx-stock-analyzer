from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.application.market_data.calendar_source_authenticity import (
    CalendarSourceAuthenticityError,
)
from app.application.market_data.review_calendar_evidence_authenticity import (
    ReviewCalendarEvidenceAuthenticity,
)
from app.application.security.identity import AuthenticatedIdentity
from app.infrastructure.persistence.sqlite_calendar_source_origin_registry import (
    SQLiteCalendarSourceOriginRegistry,
)


class CalendarSourceOriginApprovalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: str = Field(min_length=1, max_length=2048)
    publisher: str = Field(min_length=1, max_length=100)
    source_class: str = Field(min_length=1, max_length=10)
    market_scope: str = Field(min_length=1, max_length=100)
    trust_basis: str = Field(min_length=1, max_length=1000)
    registry_version: str = Field(min_length=1, max_length=100)


class CalendarSourceOriginRevocationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: str = Field(min_length=1, max_length=2048)
    reason: str = Field(min_length=1, max_length=500)
    registry_version: str = Field(min_length=1, max_length=100)


class CalendarEvidenceReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewed_claim: str = Field(min_length=1, max_length=4000)
    claim_supported: bool
    review_reason: str | None = Field(default=None, max_length=1000)


def create_calendar_source_authenticity_router(
    *,
    origin_registry: SQLiteCalendarSourceOriginRegistry,
    review_service: ReviewCalendarEvidenceAuthenticity,
    require_individual_operator,
) -> APIRouter:
    """Expose owner-only origin governance and separate evidence review, never activation."""
    router = APIRouter()

    @router.get("/api/v1/owner/session-calendar-source-origins/events")
    def list_origin_events(
        identity: AuthenticatedIdentity = Depends(require_individual_operator),
    ) -> dict[str, object]:
        try:
            origin_registry.assert_configured_owner(identity)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail="Configured source-trust owner required") from error
        return {"events": origin_registry.list_events()}

    @router.post("/api/v1/owner/session-calendar-source-origins", status_code=201)
    def approve_origin(
        payload: CalendarSourceOriginApprovalPayload,
        identity: AuthenticatedIdentity = Depends(require_individual_operator),
    ) -> dict[str, object]:
        try:
            record = origin_registry.approve_origin(
                payload.origin,
                publisher=payload.publisher,
                source_class=payload.source_class,
                market_scope=payload.market_scope,
                trust_basis=payload.trust_basis,
                registry_version=payload.registry_version,
                owner=identity,
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail="Configured source-trust owner required") from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {
            "origin": record.origin,
            "publisher": record.publisher,
            "source_class": record.source_class,
            "market_scope": record.market_scope,
            "trust_basis": record.trust_basis,
            "registry_version": record.registry_version,
            "approved_by": str(record.approved_by),
            "approved_by_credential_id": str(record.approved_by_credential_id),
            "approved_at": record.approved_at.isoformat(),
        }

    @router.post("/api/v1/owner/session-calendar-source-origins/revoke", status_code=201)
    def revoke_origin(
        payload: CalendarSourceOriginRevocationPayload,
        identity: AuthenticatedIdentity = Depends(require_individual_operator),
    ) -> dict[str, object]:
        try:
            origin_registry.revoke_origin(
                payload.origin,
                reason=payload.reason,
                registry_version=payload.registry_version,
                owner=identity,
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail="Configured source-trust owner required") from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"revoked": True, "origin": payload.origin, "registry_version": payload.registry_version}

    @router.post("/api/v1/operator/session-calendars/evidence/{evidence_id}/authenticity-review", status_code=201)
    def verify_evidence(
        evidence_id: UUID,
        payload: CalendarEvidenceReviewPayload,
        identity: AuthenticatedIdentity = Depends(require_individual_operator),
    ) -> dict[str, object]:
        try:
            record = review_service.execute(
                evidence_id,
                reviewer=identity,
                reviewed_claim=payload.reviewed_claim,
                claim_supported=payload.claim_supported,
                review_reason=payload.review_reason,
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Calendar evidence not found") from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {
            "evidence_id": str(record.evidence_id),
            "decision": record.decision.value,
            "source_origin": record.source_origin,
            "registry_version": record.registry_version,
            "artifact_sha256": record.artifact_sha256,
            "uploader_user_id": str(record.uploader_user_id),
            "verifier_user_id": str(record.verifier_user_id),
            "verified_at": record.verified_at.isoformat(),
            "reason": record.reason,
        }

    return router
