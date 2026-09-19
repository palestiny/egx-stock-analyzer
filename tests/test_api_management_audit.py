from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.identity.get_management_audit import GetManagementAudit
from app.application.identity.management_audit import (
    ManagementAuditEvent,
    ManagementAuditPage,
    ManagementAuditRecord,
)


class Audit:
    def __init__(self, records):
        self.records = records

    def append(self, event):
        raise AssertionError("read-only API must not append")

    def read_page(self, query, *, offset, limit):
        return ManagementAuditPage(
            items=tuple(self.records[offset:offset + limit]),
            total_count=len(self.records),
            has_more=offset + limit < len(self.records),
        )


def make_app(records):
    reader = GetManagementAudit(Audit(records))
    return create_app(
        InMemoryAnalysisResultStore(),
        get_management_audit=reader,
        operator_token="operator-token",
    )


def test_management_audit_api_returns_items_envelope():
    actor = uuid4()
    target = uuid4()
    record = ManagementAuditRecord(
        audit_id=7,
        event=ManagementAuditEvent(
            actor_user_id=actor,
            action="user_created",
            target_user_id=target,
            occurred_at=datetime(2026, 9, 19, tzinfo=timezone.utc),
            outcome="success",
        ),
    )

    with TestClient(make_app([record])) as client:
        response = client.get(
            "/api/v1/management/audit?page_size=50",
            headers={"Authorization": "Bearer operator-token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    assert body["items"][0]["audit_id"] == 7
    assert body["items"][0]["actor_user_id"] == str(actor)
    assert body["items"][0]["target_user_id"] == str(target)
    assert "credential" not in body["items"][0]
    assert "hash" not in body["items"][0]


def test_management_audit_api_rejects_unbounded_page_size():
    with TestClient(make_app([])) as client:
        response = client.get(
            "/api/v1/management/audit?page_size=101",
            headers={"Authorization": "Bearer operator-token"},
        )

    assert response.status_code == 400


def test_management_audit_api_requires_operator():
    with TestClient(make_app([])) as client:
        response = client.get("/api/v1/management/audit")

    assert response.status_code == 401
