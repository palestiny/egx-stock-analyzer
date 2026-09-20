from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.application.identity.get_user_audit_history import (
    GetUserAuditHistory,
    InvalidUserAuditActionError,
)
from app.application.identity.management_audit import (
    ManagementAuditEvent,
    ManagementAuditPage,
    ManagementAuditQuery,
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
        filtered = [
            record
            for record in self.records
            if record.event.target_user_id == query.target_user_id
            and (query.action is None or record.event.action == query.action)
            and (query.actions is None or record.event.action in query.actions)
        ]
        items = filtered[offset : offset + limit]
        return ManagementAuditPage(
            items=tuple(items),
            total_count=len(filtered),
            has_more=offset + limit < len(filtered),
        )


def make_record(actor, target, action="credential_rotated", outcome="success"):
    return ManagementAuditRecord(
        audit_id=len(actor.hex),
        event=ManagementAuditEvent(
            actor_user_id=actor,
            action=action,
            target_user_id=target,
            occurred_at=datetime(2026, 9, 19, tzinfo=timezone.utc),
            outcome=outcome,
        ),
    )


def test_user_history_is_target_scoped_and_redacted():
    user_id = uuid4()
    other_id = uuid4()
    operator_id = uuid4()
    store = FakeAuditStore(
        [
            make_record(operator_id, user_id, "credential_rotated_by_operator"),
            make_record(user_id, user_id, "credential_rotated"),
            make_record(user_id, other_id, "credential_rotated"),
        ]
    )

    result = GetUserAuditHistory(store).execute(AuthenticatedIdentity.user(user_id))

    assert [item.action for item in result.items] == [
        "credential_rotated_by_operator",
        "credential_rotated",
    ]
    assert {item.actor for item in result.items} == {"operator", "self"}
    assert {item.target for item in result.items} == {"self"}
    assert result.items[0].outcome == "success"

    query, offset, limit = store.queries[0]
    assert query.target_user_id == user_id
    assert set(query.actions) == {
        "user_created",
        "user_active",
        "user_disabled",
        "user_deleted",
        "credential_rotated",
        "credential_rotated_by_operator",
    }
    assert offset == 0
    assert limit == 50


def test_user_history_supports_only_allowlisted_action_filter():
    user_id = uuid4()
    store = FakeAuditStore([make_record(uuid4(), user_id)])

    result = GetUserAuditHistory(store).execute(
        AuthenticatedIdentity.user(user_id),
        action="credential_rotated",
    )

    assert result.items[0].action == "credential_rotated"

    with pytest.raises(InvalidUserAuditActionError):
        GetUserAuditHistory(store).execute(
            AuthenticatedIdentity.user(user_id),
            action="user_created_by_some_future_feature",
        )


def test_user_history_pagination_is_bounded():
    user_id = uuid4()
    store = FakeAuditStore([make_record(uuid4(), user_id)])

    with pytest.raises(ValueError):
        GetUserAuditHistory(store).execute(
            AuthenticatedIdentity.user(user_id),
            offset=-1,
        )

    with pytest.raises(Exception):
        GetUserAuditHistory(store).execute(
            AuthenticatedIdentity.user(user_id),
            page_size=101,
        )
