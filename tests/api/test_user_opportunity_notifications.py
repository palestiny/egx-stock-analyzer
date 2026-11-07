from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.alerts.get_user_opportunity_notifications import (
    GetUserOpportunityNotifications,
)
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.security.identity import LEGACY_OPERATOR_USER_ID
from app.domain.alerts.model import AlertEvent, AlertEventType
from app.infrastructure.notifications.sqlite_alert_outbox import SQLiteAlertOutbox
from app.infrastructure.notifications.sqlite_signal_alert_delivery_store import (
    SQLiteSignalAlertDeliveryStore,
)


NOW = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)


def test_authenticated_user_can_read_only_their_opportunity_notifications(tmp_path):
    database = tmp_path / "api-notifications.db"
    outbox = SQLiteAlertOutbox(database)
    deliveries = SQLiteSignalAlertDeliveryStore(database)
    event_id = uuid4()
    outbox.publish(
        AlertEvent(
            event_id=event_id,
            signal_id=uuid4(),
            symbol="EGAL",
            event_type=AlertEventType.SIGNAL_PUBLISHED,
            occurred_at=NOW,
            message="EGAL opportunity published",
        )
    )
    deliveries.create_pending(
        event_id,
        LEGACY_OPERATOR_USER_ID,
        "telegram",
        now=NOW,
    )
    query = GetUserOpportunityNotifications(
        deliveries=deliveries,
        outbox=outbox,
    )
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_user_opportunity_notifications=query,
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/me/opportunity-notifications")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 50
    assert len(payload["items"]) == 1
    assert payload["items"][0]["event_id"] == str(event_id)
    assert payload["items"][0]["symbol"] == "EGAL"
    assert payload["items"][0]["delivery"]["status"] == "PENDING"


def test_user_opportunity_notifications_rejects_invalid_limit():
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_user_opportunity_notifications=object(),
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/me/opportunity-notifications?limit=201")

    assert response.status_code == 400
