from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class LifecycleOccurrenceClaim:
    occurrence_id: str
    owner_id: str
    fencing_token: int
    attempt: int
    lease_until: datetime

    def __post_init__(self) -> None:
        if not self.occurrence_id.strip():
            raise ValueError("occurrence_id is required")
        if not self.owner_id.strip():
            raise ValueError("owner_id is required")
        if self.fencing_token < 1:
            raise ValueError("fencing_token must be positive")
        if self.attempt < 1:
            raise ValueError("attempt must be positive")
        if self.lease_until.tzinfo is None or self.lease_until.utcoffset() is None:
            raise ValueError("lease_until must be timezone-aware")


def lifecycle_occurrence_id(
    calendar_version: str,
    session_date: date,
    opportunity_id: UUID,
) -> str:
    """Return a stable, versioned identity for one calendar/session/opportunity."""
    if not calendar_version.strip():
        raise ValueError("calendar_version is required")
    identity = json.dumps(
        {
            "calendar_version": calendar_version.strip(),
            "session_date": session_date.isoformat(),
            "opportunity_id": str(opportunity_id),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return f"lifecycle-occurrence:v1:{digest}"


class LifecycleOccurrenceClaimStore(Protocol):
    def claim(
        self,
        occurrence_id: str,
        owner_id: str,
        *,
        now: datetime,
        lease_seconds: int,
    ) -> LifecycleOccurrenceClaim | None: ...

    def renew(
        self,
        claim: LifecycleOccurrenceClaim,
        *,
        now: datetime,
        lease_seconds: int,
    ) -> LifecycleOccurrenceClaim | None: ...

    def mark_failed(
        self,
        claim: LifecycleOccurrenceClaim,
        *,
        failed_at: datetime,
        reason: str,
    ) -> bool: ...
