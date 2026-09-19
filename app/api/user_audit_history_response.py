from dataclasses import asdict, dataclass
from datetime import datetime

from app.application.identity.get_user_audit_history import UserAuditHistoryPage


@dataclass(frozen=True)
class UserAuditHistoryItemResponse:
    audit_id: int
    actor: str
    target: str
    action: str
    occurred_at: datetime
    outcome: str

    @classmethod
    def from_item(cls, item):
        return cls(
            audit_id=item.audit_id,
            actor=item.actor,
            target=item.target,
            action=item.action,
            occurred_at=item.occurred_at,
            outcome=item.outcome,
        )


@dataclass(frozen=True)
class UserAuditHistoryResponse:
    items: list[dict]
    total_count: int
    offset: int
    page_size: int
    has_more: bool

    @classmethod
    def from_page(cls, page: UserAuditHistoryPage):
        return cls(
            items=[asdict(UserAuditHistoryItemResponse.from_item(item)) for item in page.items],
            total_count=page.total_count,
            offset=page.offset,
            page_size=page.page_size,
            has_more=page.has_more,
        )
