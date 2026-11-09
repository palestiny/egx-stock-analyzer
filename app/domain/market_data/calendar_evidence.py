from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4


class CalendarEvidenceKind(StrEnum):
    SCHEDULE = "SCHEDULE"
    CLOSURE = "CLOSURE"
    CANCELLATION = "CANCELLATION"
    EXCEPTIONAL_HOURS = "EXCEPTIONAL_HOURS"
    CLOSE_CONFIRMATION = "CLOSE_CONFIRMATION"


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
        )
