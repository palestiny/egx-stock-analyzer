from dataclasses import asdict, dataclass
from datetime import datetime
from uuid import UUID

from app.application.identity.get_management_audit import ManagementAuditReadPage


@dataclass(frozen=True)
class ManagementAuditItemResponse:
    audit_id: int
    actor_user_id: UUID
    target_user_id: UUID
    action: str
    occurred_at: datetime
    outcome: str

    @classmethod
    def from_record(cls, record):
        event = record.event
        return cls(
            audit_id=record.audit_id,
            actor_user_id=event.actor_user_id,
            target_user_id=event.target_user_id,
            action=event.action,
            occurred_at=event.occurred_at,
            outcome=event.outcome,
        )


@dataclass(frozen=True)
class ManagementAuditResponse:
    items: list[dict]
    total_count: int
    offset: int
    page_size: int
    has_more: bool

    @classmethod
    def from_page(cls, page: ManagementAuditReadPage):
        return cls(
            items=[asdict(ManagementAuditItemResponse.from_record(item)) for item in page.items],
            total_count=page.total_count,
            offset=page.offset,
            page_size=page.page_size,
            has_more=page.has_more,
        )
