from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.identity.get_user_audit_history import GetUserAuditHistory
from app.application.identity.management_audit import (
    ManagementAuditEvent,
    ManagementAuditPage,
    ManagementAuditRecord,
)
from app.application.security.identity import AuthenticatedIdentity


class FakeAuthenticator:
    def __init__(self, identity):
        self.identity = identity

    def authenticate(self, authorization):
        if authorization != "Bearer user-token":
            from app.application.security.authentication import AuthenticationError

            raise AuthenticationError("invalid")
        return self.identity


class Audit:
    def __init__(self, records):
        self.records = records

    def append(self, event):
        raise AssertionError("read-only API must not append")

    def read_page(self, query, *, offset, limit):
        records = [
            record
            for record in self.records
            if record.event.target_user_id == query.target_user_id
            and (
                query.actions is None
                or record.event.action in query.actions
            )
            and (
                query.action is None
                or record.event.action == query.action
            )
        ]
        return ManagementAuditPage(
            items=tuple(records[offset : offset + limit]),
            total_count=len(records),
            has_more=offset + limit < len(records),
        )


def make_app(user_id, records):
    reader = GetUserAuditHistory(Audit(records))
    return create_app(
        InMemoryAnalysisResultStore(),
        get_user_audit_history=reader,
        authenticator=FakeAuthenticator(AuthenticatedIdentity.user(user_id)),
    )


def make_record(actor, target, action):
    return ManagementAuditRecord(
        audit_id=7,
        event=ManagementAuditEvent(
            actor_user_id=actor,
            action=action,
            target_user_id=target,
            occurred_at=datetime(2026, 9, 19, tzinfo=timezone.utc),
            outcome="success",
        ),
    )


def test_user_audit_api_returns_redacted_personal_history():
    user_id = uuid4()
    operator_id = uuid4()
    other_id = uuid4()
    records = [
        make_record(operator_id, user_id, "credential_rotated_by_operator"),
        make_record(user_id, user_id, "credential_rotated"),
        make_record(user_id, other_id, "credential_rotated"),
    ]

    with TestClient(make_app(user_id, records)) as client:
        response = client.get(
            "/api/v1/users/me/audit",
            headers={"Authorization": "Bearer user-token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 2
    assert [item["actor"] for item in body["items"]] == ["operator", "self"]
    assert all(item["target"] == "self" for item in body["items"])
    assert all("actor_user_id" not in item for item in body["items"])
    assert all("target_user_id" not in item for item in body["items"])


def test_user_audit_api_requires_authentication():
    user_id = uuid4()

    with TestClient(make_app(user_id, [])) as client:
        response = client.get("/api/v1/users/me/audit")

    assert response.status_code == 401


def test_user_audit_api_rejects_unbounded_page_size():
    user_id = uuid4()

    with TestClient(make_app(user_id, [])) as client:
        response = client.get(
            "/api/v1/users/me/audit?page_size=101",
            headers={"Authorization": "Bearer user-token"},
        )

    assert response.status_code == 400
