from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.application.identity.management_audit import ManagementAuditEvent, ManagementAuditQuery
from app.infrastructure.persistence.sqlite_management_audit_store import SQLiteManagementAuditStore


def event(actor, target, action, outcome, at):
    return ManagementAuditEvent(
        actor_user_id=actor,
        action=action,
        target_user_id=target,
        occurred_at=at,
        outcome=outcome,
    )


def test_read_page_orders_newest_first_with_id_tiebreaker(tmp_path):
    store = SQLiteManagementAuditStore(tmp_path / "audit.db")
    actor = uuid4()
    target = uuid4()
    at = datetime(2026, 9, 19, 12, tzinfo=timezone.utc)

    first = event(actor, target, "user_created", "success", at)
    second = event(actor, target, "user_disabled", "success", at)
    store.append(first)
    store.append(second)

    page = store.read_page(ManagementAuditQuery(), offset=0, limit=10)

    assert [item.event for item in page.items] == [second, first]
    assert [item.audit_id for item in page.items] == [2, 1]


def test_read_page_applies_all_filters_and_bounds_results(tmp_path):
    store = SQLiteManagementAuditStore(tmp_path / "audit.db")
    actor = uuid4()
    target = uuid4()
    other = uuid4()
    base = datetime(2026, 9, 19, tzinfo=timezone.utc)

    store.append(event(actor, target, "user_created", "success", base))
    store.append(event(other, target, "user_created", "success", base + timedelta(hours=1)))
    store.append(event(actor, target, "user_disabled", "success", base + timedelta(hours=2)))
    store.append(event(actor, other, "user_created", "failure", base + timedelta(hours=3)))

    query = ManagementAuditQuery(
        actor_user_id=actor,
        target_user_id=target,
        action="user_created",
        outcome="success",
        from_time=base,
        to_time=base + timedelta(hours=2),
    )
    page = store.read_page(query, offset=0, limit=1)

    assert page.total_count == 1
    assert len(page.items) == 1
    assert page.has_more is False
