from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum
import re
from uuid import UUID, uuid4


class CalendarEvidenceKind(StrEnum):
    SCHEDULE = "SCHEDULE"
    CLOSURE = "CLOSURE"
    CANCELLATION = "CANCELLATION"
    EXCEPTIONAL_HOURS = "EXCEPTIONAL_HOURS"
    CLOSE_CONFIRMATION = "CLOSE_CONFIRMATION"
    OPEN_CONFIRMATION = "OPEN_CONFIRMATION"



class CalendarEvidenceSourceClass(StrEnum):
    A = "A"
    A_R = "A-R"
    B = "B"
    C = "C"


class CalendarArtifactRetention(StrEnum):
    ARCHIVED = "ARCHIVED"
    EXTERNAL_ONLY = "EXTERNAL_ONLY"


@dataclass(frozen=True)
class CalendarEvidence:
    """Immutable source evidence supporting one explicit calendar-day claim."""

    evidence_id: UUID
    calendar_version: str
    session_date: date
    evidence_kind: CalendarEvidenceKind
    source_type: str
    source_reference: str
    claim: str
    recorded_by: UUID
    observed_at: datetime
    recorded_at: datetime
    source_published_at: datetime | None = None
    supersedes_evidence_id: UUID | None = None
    supersession_reason: str | None = None
    content_sha256: str = ""
    source_class: CalendarEvidenceSourceClass | None = None
    source_publisher: str | None = None
    market_scope: str | None = None
    effective_from: date | None = None
    effective_through: date | None = None
    retrieved_at: datetime | None = None
    artifact_sha256: str | None = None
    artifact_retention: CalendarArtifactRetention | None = None
    artifact_storage_reference: str | None = None
    artifact_not_retained_reason: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "calendar_version",
            "source_type",
            "source_reference",
            "claim",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be non-empty")
        for field_name in ("observed_at", "recorded_at"):
            value = getattr(self, field_name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")
        if self.source_published_at is not None and (
            self.source_published_at.tzinfo is None
            or self.source_published_at.utcoffset() is None
        ):
            raise ValueError("source_published_at must be timezone-aware")
        policy_values = (
            self.source_class, self.source_publisher, self.market_scope,
            self.effective_from, self.effective_through, self.retrieved_at,
            self.artifact_sha256, self.artifact_retention,
        )
        if any(value is not None for value in policy_values):
            if any(value is None for value in policy_values):
                raise ValueError("All source acceptance and artifact retention metadata is required together")
            assert self.source_class is not None
            assert self.artifact_retention is not None
            for name in ("source_publisher", "market_scope"):
                value = getattr(self, name)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{name} must be non-empty")
            if self.effective_through < self.effective_from:
                raise ValueError("effective_through cannot precede effective_from")
            if not self.effective_from <= self.session_date <= self.effective_through:
                raise ValueError("Evidence session date must be inside the source effective date scope")
            if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
                raise ValueError("retrieved_at must be timezone-aware")
            if not re.fullmatch(r"[0-9a-f]{64}", self.artifact_sha256):
                raise ValueError("artifact_sha256 must be a lowercase SHA-256 hex digest")
            if self.source_class is CalendarEvidenceSourceClass.A and self.source_publisher != "EGX":
                raise ValueError("Source class A requires the declared publisher EGX")
            if self.source_class is CalendarEvidenceSourceClass.A_R and self.source_publisher != "FRA":
                raise ValueError("Source class A-R requires the declared publisher FRA")
            if self.artifact_retention is CalendarArtifactRetention.ARCHIVED:
                if not self.artifact_storage_reference or self.artifact_not_retained_reason:
                    raise ValueError("ARCHIVED evidence requires artifact_storage_reference only")
            elif not self.artifact_not_retained_reason or self.artifact_storage_reference:
                raise ValueError("EXTERNAL_ONLY evidence requires artifact_not_retained_reason and no storage reference")
        elif any(value is not None for value in (self.artifact_storage_reference, self.artifact_not_retained_reason)):
            raise ValueError("Artifact retention details require source acceptance metadata")
        if self.supersedes_evidence_id is None and self.supersession_reason is not None:
            raise ValueError("supersession_reason requires supersedes_evidence_id")
        if self.supersedes_evidence_id is not None and not (
            self.supersession_reason and self.supersession_reason.strip()
        ):
            raise ValueError("supersession_reason is required when superseding evidence")

    @classmethod
    def create(
        cls,
        *,
        calendar_version: str,
        session_date: date,
        evidence_kind: CalendarEvidenceKind,
        source_type: str,
        source_reference: str,
        claim: str,
        recorded_by: UUID,
        observed_at: datetime,
        source_published_at: datetime | None = None,
        supersedes_evidence_id: UUID | None = None,
        supersession_reason: str | None = None,
        evidence_id: UUID | None = None,
        recorded_at: datetime | None = None,
        source_class: CalendarEvidenceSourceClass | None = None,
        source_publisher: str | None = None,
        market_scope: str | None = None,
        effective_from: date | None = None,
        effective_through: date | None = None,
        retrieved_at: datetime | None = None,
        artifact_sha256: str | None = None,
        artifact_retention: CalendarArtifactRetention | None = None,
        artifact_storage_reference: str | None = None,
        artifact_not_retained_reason: str | None = None,
    ) -> "CalendarEvidence":
        return cls(
            evidence_id=evidence_id or uuid4(),
            calendar_version=calendar_version,
            session_date=session_date,
            evidence_kind=evidence_kind,
            source_type=source_type,
            source_reference=source_reference,
            claim=claim,
            recorded_by=recorded_by,
            observed_at=observed_at,
            recorded_at=recorded_at or datetime.now(timezone.utc),
            source_published_at=source_published_at,
            supersedes_evidence_id=supersedes_evidence_id,
            supersession_reason=supersession_reason,
            source_class=source_class,
            source_publisher=source_publisher,
            market_scope=market_scope,
            effective_from=effective_from,
            effective_through=effective_through,
            retrieved_at=retrieved_at,
            artifact_sha256=artifact_sha256,
            artifact_retention=artifact_retention,
            artifact_storage_reference=artifact_storage_reference,
            artifact_not_retained_reason=artifact_not_retained_reason,
        )
