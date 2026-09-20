from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.identity.management_audit import (
    ManagementAuditQuery,
    ManagementAuditStore,
)
from app.application.security.identity import AuthenticatedIdentity, Permission

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100

USER_VISIBLE_ACTIONS = frozenset(
    {
        "user_created",
        "user_active",
        "user_disabled",
        "user_deleted",
        "credential_rotated",
        "credential_rotated_by_operator",
    }
)


class InvalidUserAuditPageSizeError(ValueError):
    pass


class InvalidUserAuditActionError(ValueError):
    pass


@dataclass(frozen=True)
class UserAuditHistoryItem:
    audit_id: int
    actor: str
    target: str
    action: str
    occurred_at: datetime
    outcome: str


@dataclass(frozen=True)
class UserAuditHistoryPage:
    items: tuple[UserAuditHistoryItem, ...]
    total_count: int
    has_more: bool
    offset: int
    page_size: int


class GetUserAuditHistory:
    def __init__(self, audit_store: ManagementAuditStore) -> None:
        self._audit_store = audit_store

    def execute(
        self,
        identity: AuthenticatedIdentity,
        *,
        action: str | None = None,
        outcome: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> UserAuditHistoryPage:
        if identity.user_id is None:
            raise ValueError("Authenticated user identity is required")
        if identity.user_status is None:
            raise ValueError("Authenticated user status is required")
        if page_size < 1 or page_size > MAX_PAGE_SIZE:
            raise InvalidUserAuditPageSizeError(
                f"page_size must be between 1 and {MAX_PAGE_SIZE}"
            )
        if offset < 0:
            raise ValueError("offset cannot be negative")
        if from_time is not None and from_time.tzinfo is None:
            raise ValueError("from_time must include a timezone")
        if to_time is not None and to_time.tzinfo is None:
            raise ValueError("to_time must include a timezone")
        if from_time is not None and to_time is not None and from_time >= to_time:
            raise ValueError("from_time must be earlier than to_time")
        if action is not None and action not in USER_VISIBLE_ACTIONS:
            raise InvalidUserAuditActionError("Action is not available in user audit history")

        query = ManagementAuditQuery(
            target_user_id=identity.user_id,
            action=action,
            actions=tuple(sorted(USER_VISIBLE_ACTIONS)) if action is None else (action,),
            outcome=outcome,
            from_time=from_time,
            to_time=to_time,
        )
        page = self._audit_store.read_page(query, offset=offset, limit=page_size)

        items = tuple(
            UserAuditHistoryItem(
                audit_id=record.audit_id,
                actor=(
                    "self"
                    if record.event.actor_user_id == identity.user_id
                    else "operator"
                ),
                target="self",
                action=record.event.action,
                occurred_at=record.event.occurred_at,
                outcome=record.event.outcome,
            )
            for record in page.items
        )
        return UserAuditHistoryPage(
            items=items,
            total_count=page.total_count,
            has_more=page.has_more,
            offset=offset,
            page_size=page_size,
        )
