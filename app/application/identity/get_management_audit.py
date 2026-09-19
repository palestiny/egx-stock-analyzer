from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.identity.management_audit import (
    ManagementAuditPage,
    ManagementAuditQuery,
    ManagementAuditStore,
)
from app.application.security.authorization import OperatorAuthorizer
from app.application.security.identity import AuthenticatedIdentity, Permission


DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


class InvalidManagementAuditPageSizeError(ValueError):
    pass


@dataclass(frozen=True)
class ManagementAuditReadPage:
    items: tuple
    total_count: int
    has_more: bool
    offset: int
    page_size: int


class GetManagementAudit:
    def __init__(self, audit_store: ManagementAuditStore) -> None:
        self._audit_store = audit_store
        self._operator = OperatorAuthorizer()

    def execute(
        self,
        actor: AuthenticatedIdentity,
        *,
        actor_user_id: UUID | None = None,
        target_user_id: UUID | None = None,
        action: str | None = None,
        outcome: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> ManagementAuditReadPage:
        self._operator.require(actor, Permission.OPERATOR)
        if page_size < 1 or page_size > MAX_PAGE_SIZE:
            raise InvalidManagementAuditPageSizeError(
                f"page_size must be between 1 and {MAX_PAGE_SIZE}"
            )
        if offset < 0:
            raise ValueError("offset cannot be negative")
        if from_time is not None and to_time is not None and from_time >= to_time:
            raise ValueError("from_time must be earlier than to_time")

        query = ManagementAuditQuery(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action=action,
            outcome=outcome,
            from_time=from_time,
            to_time=to_time,
        )
        page = self._audit_store.read_page(query, offset=offset, limit=page_size)
        return ManagementAuditReadPage(
            items=tuple(page.items),
            total_count=page.total_count,
            has_more=page.has_more,
            offset=offset,
            page_size=page_size,
        )
