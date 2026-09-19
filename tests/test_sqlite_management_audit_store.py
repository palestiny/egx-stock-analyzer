from uuid import uuid4

from app.application.identity.management_audit import ManagementAuditEvent
from app.infrastructure.persistence.sqlite_management_audit_store import SQLiteManagementAuditStore

def test_audit_events_persist_and_reload(tmp_path):
    store = SQLiteManagementAuditStore(tmp_path / "audit.db")
    event = ManagementAuditEvent(
        actor_user_id=uuid4(),
        action="user_created",
        target_user_id=uuid4(),
        occurred_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        outcome="success",
    )
    store.append(event)
    reloaded = SQLiteManagementAuditStore(tmp_path / "audit.db")
    assert reloaded.list_events() == [event]

def test_audit_store_does_not_accept_raw_credential_fields():
    assert not hasattr(ManagementAuditEvent, "secret")
