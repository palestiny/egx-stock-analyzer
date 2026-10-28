from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.infrastructure.persistence.sqlite_subscription_store import SQLiteSubscriptionStore


TOKEN = "operator-test-token"


def make_client(tmp_path):
    store = SQLiteSubscriptionStore(tmp_path / "subscriptions.db")
    app = create_app(
        result_store=InMemoryAnalysisResultStore(),
        operator_token=TOKEN,
        subscription_store=store,
    )
    return TestClient(app), store


def auth():
    return {"Authorization": f"Bearer {TOKEN}"}


def test_subscription_admin_routes_create_plan_pending_subscription_and_audited_transition(tmp_path):
    client, store = make_client(tmp_path)
    now = datetime.now(timezone.utc)
    plan_response = client.post(
        "/api/v1/owner/subscription-plans",
        headers=auth(),
        json={
            "plan_id": "pilot",
            "version": 1,
            "display_name": "Pilot",
            "active": True,
            "entitlements": [
                {"code": "telegram_opportunities", "enabled": True, "limit": 50}
            ],
        },
    )
    assert plan_response.status_code == 200
    assert plan_response.json()["plan_id"] == "pilot"
    assert client.get(
        "/api/v1/owner/subscription-plans/pilot/1",
        headers=auth(),
    ).json()["entitlements"][0]["code"] == "telegram_opportunities"

    user_id = uuid4()
    create_response = client.post(
        "/api/v1/owner/subscriptions",
        headers=auth(),
        json={
            "user_id": str(user_id),
            "plan_id": "pilot",
            "plan_version": 1,
            "starts_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(days=30)).isoformat(),
            "reason": "Manual pilot provisioning; payment is not implied",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["status"] == "PENDING"
    assert created["payment_provider"] is None
    subscription_id = created["subscription_id"]

    transition_response = client.post(
        f"/api/v1/owner/subscriptions/{subscription_id}/transition",
        headers=auth(),
        json={"status": "ACTIVE", "reason": "Operator verified pilot access"},
    )
    assert transition_response.status_code == 200
    assert transition_response.json()["status"] == "ACTIVE"
    assert client.get(
        f"/api/v1/owner/subscriptions/{subscription_id}",
        headers=auth(),
    ).json()["status"] == "ACTIVE"
    assert store.latest_for_user(user_id).status.value == "ACTIVE"


def test_subscription_admin_routes_require_operator_authentication(tmp_path):
    client, _store = make_client(tmp_path)

    response = client.get("/api/v1/owner/subscription-plans/pilot/1")

    assert response.status_code == 401


def test_subscription_admin_rejects_naive_subscription_timestamps(tmp_path):
    client, _store = make_client(tmp_path)
    client.post(
        "/api/v1/owner/subscription-plans",
        headers=auth(),
        json={
            "plan_id": "pilot",
            "version": 1,
            "display_name": "Pilot",
            "entitlements": [{"code": "telegram_opportunities"}],
        },
    )

    response = client.post(
        "/api/v1/owner/subscriptions",
        headers=auth(),
        json={
            "user_id": str(uuid4()),
            "plan_id": "pilot",
            "plan_version": 1,
            "starts_at": "2026-10-28T09:00:00",
            "expires_at": "2026-11-28T09:00:00+00:00",
            "reason": "test",
        },
    )

    assert response.status_code == 422
    assert "starts_at must include a timezone" in response.json()["detail"]


def test_subscription_admin_maps_missing_subscription_transition_to_404(tmp_path):
    client, _store = make_client(tmp_path)

    response = client.post(
        f"/api/v1/owner/subscriptions/{uuid4()}/transition",
        headers=auth(),
        json={"status": "ACTIVE", "reason": "test"},
    )

    assert response.status_code == 404
