from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.application.identity.get_user_audit_history import GetUserAuditHistory
from app.application.identity.management_audit import (
    ManagementAuditEvent,
    ManagementAuditPage,
    ManagementAuditRecord,
)
from app.application.security.authorization import AuthorizationError
from app.application.security.identity import AuthenticatedIdentity


class StubAuditStore:
    def __init__(self, records):
        self.records = tuple(records)
        self.last_query = None

    def append(self, event):
        raise AssertionError("append is not expected")

    def read_page(self, query, *, offset, limit):
        self.last_query = query
        return ManagementAuditPage(
            items=self.records,
            total_count=len(self.records),
            has_more=False,
        )


def test_user_audit_history_is_scoped_to_authenticated_user() -> None:
    user_id = UUID("10000000-0000-0000-0000-000000000001")
    other_id = UUID("20000000-0000-0000-0000-000000000001")
    store = StubAuditStore(
        [
            ManagementAuditRecord(
                audit_id=1,
                event=ManagementAuditEvent(
                    actor_user_id=user_id,
                    target_user_id=user_id,
                    action="credential_rotated",
                    occurred_at=datetime.now(timezone.utc),
                    outcome="success",
                ),
            )
        ]
    )

    page = GetUserAuditHistory(store).execute(
        AuthenticatedIdentity.user(user_id),
    )

    assert store.last_query.target_user_id == user_id
    assert store.last_query.target_user_id != other_id
    assert all(item.target == "self" for item in page.items)
    assert all(item.actor == "self" for item in page.items)


def test_user_audit_history_never_accepts_another_user_as_scope() -> None:
    user_id = UUID("10000000-0000-0000-0000-000000000002")
    store = StubAuditStore([])

    # The API/application contract derives the target scope from identity;
    # there is deliberately no target_user_id parameter to override it.
    page = GetUserAuditHistory(store).execute(
        AuthenticatedIdentity.user(user_id),
    )

    assert page.items == ()
    assert store.last_query.target_user_id == user_id


def test_operator_identity_cannot_use_owner_scoped_user_audit_history() -> None:
    store = StubAuditStore([])

    with pytest.raises(ValueError, match="Authenticated user identity is required"):
        GetUserAuditHistory(store).execute(AuthenticatedIdentity.operator())
