from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.application.market_data.calendar_source_authenticity import (
    CalendarEvidenceVerificationRecord,
    CalendarSourceAuthenticityError,
    CalendarSourceAuthenticityVerifier,
)
from app.application.security.identity import AuthenticatedIdentity
from app.domain.market_data.calendar_evidence import CalendarEvidence


class CalendarEvidenceRepository(Protocol):
    def get(self, evidence_id: UUID) -> CalendarEvidence | None: ...


class CalendarEvidenceUploaderIdentityResolver(Protocol):
    def resolve(self, evidence: CalendarEvidence) -> AuthenticatedIdentity | None: ...


class ReviewCalendarEvidenceAuthenticity:
    """Bind a human reviewer to the immutable evidence uploader before verification."""

    def __init__(
        self,
        *,
        evidence_repository: CalendarEvidenceRepository,
        uploader_identity_resolver: CalendarEvidenceUploaderIdentityResolver,
        verifier: CalendarSourceAuthenticityVerifier,
    ) -> None:
        self._evidence_repository = evidence_repository
        self._uploader_identity_resolver = uploader_identity_resolver
        self._verifier = verifier

    def execute(
        self,
        evidence_id: UUID,
        *,
        reviewer: AuthenticatedIdentity,
        reviewed_claim: str,
        claim_supported: bool,
        review_reason: str | None = None,
        at: datetime | None = None,
    ) -> CalendarEvidenceVerificationRecord:
        evidence = self._evidence_repository.get(evidence_id)
        if evidence is None:
            raise KeyError(f"Calendar evidence {evidence_id} does not exist")
        uploader = self._uploader_identity_resolver.resolve(evidence)
        if uploader is None:
            raise CalendarSourceAuthenticityError(
                "Evidence uploader no longer has an active individual operator credential"
            )
        return self._verifier.verify_for_activation(
            evidence,
            uploader=uploader,
            verifier=reviewer,
            reviewed_claim=reviewed_claim,
            claim_supported=claim_supported,
            review_reason=review_reason,
            at=at,
        )
