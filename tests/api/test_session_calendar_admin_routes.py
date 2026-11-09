from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.security.authentication import AuthenticationError
from app.application.security.identity import AuthenticatedIdentity
from app.infrastructure.persistence.sqlite_session_calendar_repository import (
    SQLiteSessionCalendarRepository,
)


OPERATOR_TOKEN = "calendar-operator-token"
USER_TOKEN = "calendar-user-token"
USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class CalendarTestAuthenticator:
    def authenticate(self, authorization_header: str | None) -> AuthenticatedIdentity:
        if authorization_header == f"Bearer {OPERATOR_TOKEN}":
            return AuthenticatedIdentity.operator()
        if authorization_header == f"Bearer {USER_TOKEN}":
            return AuthenticatedIdentity.user(USER_ID)
        raise AuthenticationError("Invalid credentials")


def make_client(tmp_path):
    store = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    app = create_app(
        result_store=InMemoryAnalysisResultStore(),
        authenticator=CalendarTestAuthenticator(),
        session_calendar_store=store,
    )
    return TestClient(app), store


def operator_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {OPERATOR_TOKEN}"}


def calendar_payload() -> dict[str, object]:
    return {
        "version": "egx-2026-11-v1",
        "timezone": "Africa/Cairo",
        "coverage_start": "2026-11-01",
        "coverage_end": "2026-11-02",
        "days": [
            {"date": "2026-11-01", "status": "NON_TRADING"},
            {
                "date": "2026-11-02",
                "status": "CLOSED",
                "session_open": "10:00",
                "session_close": "14:30",
                "closed_at": "2026-11-02T14:31:00+02:00",
            },
        ],
        "source_reference": "https://egx.com.eg/official-notice/123",
        "reason": "Publish operator-verified calendar sample",
    }


def test_operator_can_publish_list_and_read_calendar_version(tmp_path):
    client, store = make_client(tmp_path)

    published = client.post(
        "/api/v1/owner/session-calendars/versions",
        headers=operator_headers(),
        json=calendar_payload(),
    )

    assert published.status_code == 201
    body = published.json()
    assert body["version"] == "egx-2026-11-v1"
    assert body["published_by"] == "operator"
    assert body["source_reference"] == "https://egx.com.eg/official-notice/123"
    assert body["calendar"]["days"][1]["status"] == "CLOSED"
    assert len(body["sha256"]) == 64

    listed = client.get(
        "/api/v1/owner/session-calendars/versions",
        headers=operator_headers(),
    )
    assert listed.status_code == 200
    assert [item["version"] for item in listed.json()["items"]] == ["egx-2026-11-v1"]
    assert "calendar" not in listed.json()["items"][0]

    loaded = client.get(
        "/api/v1/owner/session-calendars/versions/egx-2026-11-v1",
        headers=operator_headers(),
    )
    assert loaded.status_code == 200
    assert loaded.json()["calendar"] == body["calendar"]
    assert store.get_version("egx-2026-11-v1").published_by == "operator"


def test_calendar_management_requires_operator_authentication(tmp_path):
    client, _store = make_client(tmp_path)

    response = client.get("/api/v1/owner/session-calendars/versions")

    assert response.status_code == 401


def test_calendar_management_rejects_authenticated_non_operator(tmp_path):
    client, _store = make_client(tmp_path)

    response = client.get(
        "/api/v1/owner/session-calendars/versions",
        headers={"Authorization": f"Bearer {USER_TOKEN}"},
    )

    assert response.status_code == 403


def test_publication_actor_cannot_be_spoofed_in_request_payload(tmp_path):
    client, _store = make_client(tmp_path)
    payload = {**calendar_payload(), "published_by": "forged-admin"}

    response = client.post(
        "/api/v1/owner/session-calendars/versions",
        headers=operator_headers(),
        json=payload,
    )

    assert response.status_code == 422


def test_publication_rejects_calendar_coverage_gaps(tmp_path):
    client, store = make_client(tmp_path)
    payload = calendar_payload()
    payload["days"] = [payload["days"][0]]

    response = client.post(
        "/api/v1/owner/session-calendars/versions",
        headers=operator_headers(),
        json=payload,
    )

    assert response.status_code == 422
    assert "every date" in response.json()["detail"]
    assert store.list_versions() == ()


def test_publication_rejects_invalid_timezone_and_dates(tmp_path):
    client, store = make_client(tmp_path)
    payload = {**calendar_payload(), "timezone": "Not/A_Timezone"}

    response = client.post(
        "/api/v1/owner/session-calendars/versions",
        headers=operator_headers(),
        json=payload,
    )

    assert response.status_code == 422
    assert store.list_versions() == ()


def test_duplicate_calendar_version_returns_conflict(tmp_path):
    client, _store = make_client(tmp_path)
    first = client.post(
        "/api/v1/owner/session-calendars/versions",
        headers=operator_headers(),
        json=calendar_payload(),
    )
    second = client.post(
        "/api/v1/owner/session-calendars/versions",
        headers=operator_headers(),
        json=calendar_payload(),
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_publishing_does_not_implicitly_activate_calendar(tmp_path):
    client, _store = make_client(tmp_path)
    published = client.post(
        "/api/v1/owner/session-calendars/versions",
        headers=operator_headers(),
        json=calendar_payload(),
    )
    assert published.status_code == 201

    response = client.get(
        "/api/v1/owner/session-calendars/active",
        headers=operator_headers(),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No active session calendar"


def test_activation_events_endpoint_is_empty_before_any_activation(tmp_path):
    client, _store = make_client(tmp_path)

    response = client.get(
        "/api/v1/owner/session-calendars/activation-events",
        headers=operator_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_calendar_management_returns_service_unavailable_without_store():
    app = create_app(
        result_store=InMemoryAnalysisResultStore(),
        operator_token=OPERATOR_TOKEN,
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/owner/session-calendars/versions",
            headers=operator_headers(),
        )

    assert response.status_code == 503



def test_publication_rejects_naive_session_close_confirmation(tmp_path):
    client, store = make_client(tmp_path)
    payload = calendar_payload()
    payload["days"] = [
        payload["days"][0],
        {
            **payload["days"][1],
            "closed_at": "2026-11-02T14:31:00",
        },
    ]

    response = client.post(
        "/api/v1/owner/session-calendars/versions",
        headers=operator_headers(),
        json=payload,
    )

    assert response.status_code == 422
    assert "timezone-aware" in response.json()["detail"]
    assert store.list_versions() == ()


def test_publication_rejects_blank_audit_metadata(tmp_path):
    client, store = make_client(tmp_path)
    payload = {**calendar_payload(), "source_reference": "   "}

    response = client.post(
        "/api/v1/owner/session-calendars/versions",
        headers=operator_headers(),
        json=payload,
    )

    assert response.status_code == 422
    assert store.list_versions() == ()
