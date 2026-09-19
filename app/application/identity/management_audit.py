from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ManagementAuditEvent:
    actor_user_id: UUID
    action: str
    target_user_id: UUID
    occurred_at: datetime
    outcome: str


@dataclass(frozen=True)
class ManagementAuditRecord:
    audit_id: int
    event: ManagementAuditEvent


@dataclass(frozen=True)
class ManagementAuditQuery:
    actor_user_id: UUID | None = None
    target_user_id: UUID | None = None
    action: str | None = None
    outcome: str | None = None
    from_time: datetime | None = None
    to_time: datetime | None = None


@dataclass(frozen=True)
class ManagementAuditPage:
    items: tuple[ManagementAuditRecord, ...]
    total_count: int
    has_more: bool


class ManagementAuditStore(Protocol):
    def append(self, event: ManagementAuditEvent) -> None:
        ...

    def read_page(
        self,
        query: ManagementAuditQuery,
        *,
        offset: int,
        limit: int,
    ) -> ManagementAuditPage:
        ...
