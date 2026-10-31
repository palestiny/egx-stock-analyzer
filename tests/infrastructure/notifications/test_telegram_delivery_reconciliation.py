from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.infrastructure.notifications.sqlite_signal_alert_delivery_store import (
    SQLiteSignalAlertDeliveryStore,
)
from app.infrastructure.notifications.sqlite_telegram_delivery_reconciliation_store import (
    SQLiteTelegramDeliveryReconciliationStore,
)


NOW = datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc)


def make_delivery(tmp_path, status="DELIVERY_UNKNOWN"):
    path = tmp_path / "telegram-reconciliation.db"
    deliveries = SQLiteSignalAlertDeliveryStore(path)
    event_id, user_id = uuid4(), uuid4()
    deliveries.create_pending(event_id, user_id, "telegram", now=NOW)
    if status == "FAILED":
        deliveries.mark_failed(event_id, user_id, "telegram", "provider rejected", now=NOW)
    elif status == "DELIVERY_UNKNOWN":
        token = uuid4()
        assert deliveries.claim(
            event_id, user_id, "telegram", claim_token=token,
            now=NOW, lease_until=NOW.replace(minute=1),
        )
        assert deliveries.mark_sending(
            event_id, user_id, "telegram", claim_token=token, now=NOW,
        )
        assert deliveries.mark_delivery_unknown(
            event_id, user_id, "telegram", "transport outcome unknown",
            claim_token=token, now=NOW,
        )
    store = SQLiteTelegramDeliveryReconciliationStore(path)
    return deliveries, store, event_id, user_id


def test_reconciliation_is_atomic_audited_and_not_repeatable_after_resolution(tmp_path):
    deliveries, store, event_id, user_id = make_delivery(tmp_path)

    result = store.reconcile(
        event_id, user_id, "telegram",
        outcome="CONFIRMED_DELIVERED",
        actor_subject="operator-123",
        reason="Verified in Telegram conversation history",
        now=NOW,
    )

    assert result.previous_status == "DELIVERY_UNKNOWN"
    assert result.new_status == "DELIVERED"
    record = deliveries.get(event_id, user_id, "telegram")
    assert record is not None and record.status.value == "DELIVERED"
    audit = store.list_audit()
    assert len(audit) == 1
    assert audit[0].actor_subject == "operator-123"
    assert audit[0].reason == "Verified in Telegram conversation history"
    assert audit[0].outcome == "CONFIRMED_DELIVERED"
    with pytest.raises(ValueError, match="not eligible"):
        store.reconcile(
            event_id, user_id, "telegram",
            outcome="CONFIRMED_NOT_DELIVERED",
            actor_subject="operator-123",
            reason="Conflicting second decision",
            now=NOW,
        )
    assert len(store.list_audit()) == 1


def test_confirmed_not_delivered_becomes_terminal_and_does_not_requeue(tmp_path):
    deliveries, store, event_id, user_id = make_delivery(tmp_path)

    result = store.reconcile(
        event_id, user_id, "telegram",
        outcome="CONFIRMED_NOT_DELIVERED",
        actor_subject="operator-456",
        reason="Checked recipient and Telegram history",
        now=NOW,
    )

    assert result.new_status == "NOT_DELIVERED"
    record = deliveries.get(event_id, user_id, "telegram")
    assert record is not None and record.status.value == "NOT_DELIVERED"
    assert record.claim_token is None
    assert record.lease_until is None
    assert deliveries.claim(
        event_id, user_id, "telegram", claim_token=uuid4(),
        now=NOW, lease_until=NOW.replace(minute=1),
    ) is False
    assert store.list_unresolved() == ()


def test_reconciliation_rejects_missing_actor_reason_and_bad_page(tmp_path):
    _deliveries, store, event_id, user_id = make_delivery(tmp_path)
    with pytest.raises(ValueError, match="actor identity"):
        store.reconcile(
            event_id, user_id, "telegram",
            outcome="CONFIRMED_DELIVERED", actor_subject=" ",
            reason="verified", now=NOW,
        )
    with pytest.raises(ValueError, match="reason"):
        store.reconcile(
            event_id, user_id, "telegram",
            outcome="CONFIRMED_DELIVERED", actor_subject="operator",
            reason=" ", now=NOW,
        )
    with pytest.raises(ValueError, match="limit"):
        store.list_unresolved(limit=0)


def test_operator_api_lists_reconciles_and_exposes_audit(tmp_path):
    _deliveries, store, event_id, user_id = make_delivery(tmp_path)
    app = create_app(
        InMemoryAnalysisResultStore(),
        operator_token="operator-token",
        telegram_delivery_reconciliation_store=store,
    )
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer operator-token"}
        listing = client.get(
            "/api/v1/management/telegram-deliveries/unresolved",
            headers=headers,
        )
        assert listing.status_code == 200
        assert listing.json()["items"][0]["status"] == "DELIVERY_UNKNOWN"

        reconciled = client.post(
            f"/api/v1/management/telegram-deliveries/{event_id}/{user_id}/reconcile",
            headers=headers,
            json={
                "outcome": "CONFIRMED_NOT_DELIVERED",
                "reason": "Operator verified message was not received",
            },
        )
        assert reconciled.status_code == 200
        assert reconciled.json()["actor_subject"] == "operator"

        audit = client.get(
            "/api/v1/management/telegram-deliveries/reconciliation-audit",
            headers=headers,
        )
        assert audit.status_code == 200
        assert len(audit.json()["items"]) == 1
        assert audit.json()["items"][0]["reason"] == "Operator verified message was not received"

        repeated = client.post(
            f"/api/v1/management/telegram-deliveries/{event_id}/{user_id}/reconcile",
            headers=headers,
            json={"outcome": "CONFIRMED_DELIVERED", "reason": "Second decision"},
        )
        assert repeated.status_code == 409


def test_reconciliation_api_requires_operator_authentication(tmp_path):
    _deliveries, store, _event_id, _user_id = make_delivery(tmp_path)
    app = create_app(
        InMemoryAnalysisResultStore(),
        operator_token="operator-token",
        telegram_delivery_reconciliation_store=store,
    )
    with TestClient(app) as client:
        response = client.get("/api/v1/management/telegram-deliveries/unresolved")
    assert response.status_code == 401
