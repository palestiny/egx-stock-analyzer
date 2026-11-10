from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.security.authentication import AuthenticationError
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.infrastructure.persistence.sqlite_calendar_evidence_repository import SQLiteCalendarEvidenceRepository
from app.infrastructure.persistence.sqlite_calendar_publication_unit_of_work import SQLiteCalendarPublicationUnitOfWork
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore
from app.domain.identity.user import User, UserStatus
from app.infrastructure.persistence.sqlite_session_calendar_repository import (
    SQLiteSessionCalendarRepository,
)


OPERATOR_TOKEN = "calendar-operator-token"
LEGACY_OPERATOR_TOKEN = "legacy-shared-operator-token"
OPERATOR_USER_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
OPERATOR_CREDENTIAL_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
USER_TOKEN = "calendar-user-token"
USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class CalendarTestAuthenticator:
    def authenticate(self, authorization_header: str | None) -> AuthenticatedIdentity:
        if authorization_header == f"Bearer {OPERATOR_TOKEN}":
            return AuthenticatedIdentity.user(
                OPERATOR_USER_ID,
                credential_id=OPERATOR_CREDENTIAL_ID,
                permissions=frozenset({Permission.OPERATOR}),
            )
        if authorization_header == f"Bearer {LEGACY_OPERATOR_TOKEN}":
            return AuthenticatedIdentity.operator()
        if authorization_header == f"Bearer {USER_TOKEN}":
            return AuthenticatedIdentity.user(USER_ID)
        raise AuthenticationError("Invalid credentials")


def make_client(tmp_path):
    database = tmp_path / "calendar.db"
    store = SQLiteSessionCalendarRepository(database)
    evidence_repository = SQLiteCalendarEvidenceRepository(database)
    SQLiteUserStore(database).save(User(OPERATOR_USER_ID, UserStatus.ACTIVE))
    publication_uow = SQLiteCalendarPublicationUnitOfWork(store, evidence_repository)
    app = create_app(
        result_store=InMemoryAnalysisResultStore(),
        authenticator=CalendarTestAuthenticator(),
        session_calendar_store=store,
        calendar_publication_uow=publication_uow,
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
        "evidence": [
            {
                "session_date": "2026-11-01",
                "evidence_kind": "CLOSURE",
                "source_type": "OFFICIAL_EXCHANGE_NOTICE",
                "source_class": "A",
                "source_publisher": "EGX",
                "market_scope": "EGX_MARKET_WIDE",
                "effective_from": "2026-11-01",
                "effective_through": "2026-11-01",
                "retrieved_at": "2026-11-01T09:00:00+02:00",
                "artifact_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
                "artifact_retention": "EXTERNAL_ONLY",
                "artifact_not_retained_reason": "Test fixture stores the official reference only",
                "source_reference": "https://example.invalid/egx/notice-1",
                "claim": "EGX notice confirms non-trading day",
                "observed_at": "2026-11-01T09:00:00+02:00",
            },
            {
                "session_date": "2026-11-02",
                "evidence_kind": "SCHEDULE",
                "source_type": "OFFICIAL_EXCHANGE_NOTICE",
                "source_class": "A",
                "source_publisher": "EGX",
                "market_scope": "EGX_MARKET_WIDE",
                "effective_from": "2026-11-02",
                "effective_through": "2026-11-02",
                "retrieved_at": "2026-11-02T09:00:00+02:00",
                "artifact_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
                "artifact_retention": "EXTERNAL_ONLY",
                "artifact_not_retained_reason": "Test fixture stores the official reference only",
                "source_reference": "https://example.invalid/egx/schedule-2",
                "claim": "EGX notice confirms scheduled session hours",
                "observed_at": "2026-11-02T09:00:00+02:00",
            },
            {
                "session_date": "2026-11-02",
                "evidence_kind": "CLOSE_CONFIRMATION",
                "source_type": "OFFICIAL_EXCHANGE_NOTICE",
                "source_class": "A",
                "source_publisher": "EGX",
                "market_scope": "EGX_MARKET_WIDE",
                "effective_from": "2026-11-02",
                "effective_through": "2026-11-02",
                "retrieved_at": "2026-11-02T14:31:00+02:00",
                "artifact_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                "artifact_retention": "EXTERNAL_ONLY",
                "artifact_not_retained_reason": "Test fixture stores the official reference only",
                "source_reference": "https://example.invalid/egx/notice-2",
                "claim": "EGX notice confirms session close",
                "observed_at": "2026-11-02T14:31:00+02:00",
            },
        ],
        "source_reference": "EGX notice reference 123",
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
    assert body["published_by"] == str(OPERATOR_USER_ID)
    assert body["source_reference"] == "EGX notice reference 123"
    assert body["calendar"]["days"][1]["status"] == "CLOSED"
    assert len(body["sha256"]) == 64
    assert len(body["evidence"]) == 3
    assert all(len(item["content_sha256"]) == 64 for item in body["evidence"])

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
    assert store.get_version("egx-2026-11-v1").published_by == str(OPERATOR_USER_ID)


def test_calendar_management_requires_operator_authentication(tmp_path):
    client, _store = make_client(tmp_path)

    response = client.get("/api/v1/owner/session-calendars/versions")

    assert response.status_code == 401


def test_calendar_management_rejects_legacy_shared_operator_token(tmp_path):
    client, _store = make_client(tmp_path)

    response = client.get(
        "/api/v1/owner/session-calendars/versions",
        headers={"Authorization": f"Bearer {LEGACY_OPERATOR_TOKEN}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Individually attributable operator credential required"


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
        authenticator=CalendarTestAuthenticator(),
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



def test_active_calendar_and_audit_endpoints_read_persisted_activation(tmp_path):
    client, store = make_client(tmp_path)
    published = client.post(
        "/api/v1/owner/session-calendars/versions",
        headers=operator_headers(),
        json=calendar_payload(),
    )
    assert published.status_code == 201
    store.activate(
        "egx-2026-11-v1",
        performed_by="operator",
        reason="Activate only in the isolated test fixture",
    )

    active = client.get(
        "/api/v1/owner/session-calendars/active",
        headers=operator_headers(),
    )
    assert active.status_code == 200
    assert active.json()["version"] == "egx-2026-11-v1"

    events = client.get(
        "/api/v1/owner/session-calendars/activation-events",
        headers=operator_headers(),
    )
    assert events.status_code == 200
    assert events.json()["items"][0]["action"] == "ACTIVATE"
    assert events.json()["items"][0]["performed_by"] == "operator"



def test_http_activation_is_not_exposed_before_coverage_policy_exists(tmp_path):
    client, store = make_client(tmp_path)
    published = client.post(
        "/api/v1/owner/session-calendars/versions",
        headers=operator_headers(),
        json=calendar_payload(),
    )
    assert published.status_code == 201

    response = client.post(
        "/api/v1/owner/session-calendars/versions/egx-2026-11-v1/activate",
        headers=operator_headers(),
    )

    assert response.status_code == 404
    assert store.get_active() is None
    assert store.list_activation_events() == ()



def test_publication_rejects_version_identifiers_unsafe_for_resource_routes(tmp_path):
    client, store = make_client(tmp_path)
    payload = {**calendar_payload(), "version": "egx/2026/v1"}

    response = client.post(
        "/api/v1/owner/session-calendars/versions",
        headers=operator_headers(),
        json=payload,
    )

    assert response.status_code == 422
    assert store.list_versions() == ()



def test_publication_normalizes_surrounding_whitespace_in_version_identifier(tmp_path):
    client, store = make_client(tmp_path)
    payload = {**calendar_payload(), "version": "  egx-2026-11-v1  "}

    response = client.post(
        "/api/v1/owner/session-calendars/versions",
        headers=operator_headers(),
        json=payload,
    )

    assert response.status_code == 201
    assert response.json()["version"] == "egx-2026-11-v1"
    assert store.get_version("egx-2026-11-v1") is not None



def test_authenticated_non_operator_cannot_publish_calendar(tmp_path):
    client, store = make_client(tmp_path)

    response = client.post(
        "/api/v1/owner/session-calendars/versions",
        headers={"Authorization": f"Bearer {USER_TOKEN}"},
        json=calendar_payload(),
    )

    assert response.status_code == 403
    assert store.list_versions() == ()


def test_reading_unknown_calendar_version_returns_not_found(tmp_path):
    client, _store = make_client(tmp_path)

    response = client.get(
        "/api/v1/owner/session-calendars/versions/egx-unknown-v1",
        headers=operator_headers(),
    )

    assert response.status_code == 404



class BlankSubjectOperatorAuthenticator:
    def authenticate(self, authorization_header: str | None) -> AuthenticatedIdentity:
        return AuthenticatedIdentity(
            subject=" ",
            permissions=frozenset({Permission.OPERATOR}),
        )


def test_publication_rejects_operator_identity_without_attributable_credential(tmp_path):
    store = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    app = create_app(
        result_store=InMemoryAnalysisResultStore(),
        authenticator=BlankSubjectOperatorAuthenticator(),
        session_calendar_store=store,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/owner/session-calendars/versions",
            headers=operator_headers(),
            json=calendar_payload(),
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Individually attributable operator credential required"
    assert store.list_versions() == ()
