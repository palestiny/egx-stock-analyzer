from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.application.identity.get_management_audit import (
    GetManagementAudit,
    InvalidManagementAuditPageSizeError,
    ManagementAuditQuery,
)
from app.application.identity.management_audit import (
    ManagementAuditEvent,
    ManagementAuditPage,
    ManagementAuditRecord,
)
from app.application.security.identity import AuthenticatedIdentity


class FakeAuditStore:
    def __init__(self, records):
        self.records = list(records)
        self.queries = []

    def append(self, event):
        raise AssertionError("read capability must not append")

    def read_page(self, query, offset, limit):
        self.queries.append((query, offset, limit))
        items = self.records[offset : offset + limit]
        return ManagementAuditPage(
            items=items,
            total_count=len(self.records),
            has_more=offset + limit < len(self.records),
        )


def make_record(action="user_created", outcome="success", at=None):
    return ManagementAuditRecord(
        audit_id=1,
        event=ManagementAuditEvent(
            actor_user_id=uuid4(),
            action=action,
            target_user_id=uuid4(),
            occurred_at=at or datetime.now(timezone.utc),
            outcome=outcome,
        ),
    )


def test_empty_audit_result_is_supported():
    store = FakeAuditStore([])
    result = GetManagementAudit(store).execute(AuthenticatedIdentity.operator())

    assert result.items == ()
    assert result.total_count == 0
    assert result.has_more is False


def test_audit_reader_requires_operator():
    user = AuthenticatedIdentity.user(uuid4())
    store = FakeAuditStore([])

    with pytest.raises(Exception):
        GetManagementAudit(store).execute(user)


def test_filters_are_forwarded_as_one_application_query():
    store = FakeAuditStore([make_record()])
    actor = uuid4()
    target = uuid4()
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    result = GetManagementAudit(store).execute(
        AuthenticatedIdentity.operator(),
        actor_user_id=actor,
        target_user_id=target,
        action="user_created",
        outcome="success",
        from_time=start,
        to_time=end,
        page_size=25,
        offset=50,
    )

    query, offset, limit = store.queries[0]
    assert query == ManagementAuditQuery(
        actor_user_id=actor,
        target_user_id=target,
        action="user_created",
        outcome="success",
        from_time=start,
        to_time=end,
    )
    assert (offset, limit) == (50, 25)
    assert result.items == ()


def test_page_size_is_bounded():
    store = FakeAuditStore([])

    with pytest.raises(InvalidManagementAuditPageSizeError):
        GetManagementAudit(store).execute(AuthenticatedIdentity.operator(), page_size=0)

    with pytest.raises(InvalidManagementAuditPageSizeError):
        GetManagementAudit(store).execute(AuthenticatedIdentity.operator(), page_size=101)
