from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class EntitlementGrant:
    grant_id: UUID
    user_id: UUID
    capability: str
    starts_at: datetime
    expires_at: datetime | None
    granted_by: UUID
    reason: str
    created_at: datetime
    revoked_at: datetime | None = None
    revoked_by: UUID | None = None
    revoke_reason: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("starts_at", self.starts_at),
            ("expires_at", self.expires_at),
            ("created_at", self.created_at),
            ("revoked_at", self.revoked_at),
        ):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError(f"{name} must be timezone-aware")
        if not self.capability.strip():
            raise ValueError("capability is required")
        if not self.reason.strip():
            raise ValueError("grant reason is required")
        if self.expires_at is not None and self.expires_at <= self.starts_at:
            raise ValueError("expires_at must be later than starts_at")
        if (self.revoked_at is None) != (self.revoked_by is None):
            raise ValueError("revocation timestamp and actor must be supplied together")
        if self.revoked_at is not None and not (self.revoke_reason or "").strip():
            raise ValueError("revocation reason is required")

    def active_at(self, at: datetime) -> bool:
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("evaluation time must be timezone-aware")
        return (
            self.revoked_at is None
            and self.starts_at <= at
            and (self.expires_at is None or at < self.expires_at)
        )
