from uuid import uuid4
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.notifications.delivery_store import (
    AlertDeliveryRecord,
    AlertDeliveryStatus,
)
from app.application.notifications.deliver_alert_by_symbol import (
    AlertCandidateNotFoundError,
)
from app.domain.reporting.alerts import AlertCandidate


def make_record(status: AlertDeliveryStatus) -> AlertDeliveryRecord:
    return AlertDeliveryRecord(
        stock_id=uuid4(),
        snapshot_id=uuid4(),
        channel="telegram",
        status=status,
        last_error=None if status is AlertDeliveryStatus.DELIVERED else "provider unavailable",
    )


def test_delivery_returns_503_when_delivery_is_not_configured():
    app = create_app(InMemoryAnalysisResultStore())

    with TestClient(app) as client:
        response = client.post("/api/v1/alerts/EGAL/deliver?channel=telegram")

    assert response.status_code == 503
    assert response.json() == {"detail": "Alert delivery is not configured"}


def test_delivery_returns_404_when_candidate_is_missing():
    capability = Mock()
    capability.execute.side_effect = AlertCandidateNotFoundError(
        "Alert candidate not found for EGAL"
    )
    app = create_app(
        InMemoryAnalysisResultStore(),
        deliver_alert_by_symbol=capability,
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/alerts/EGAL/deliver?channel=telegram")

    assert response.status_code == 404
    assert response.json() == {"detail": "Alert candidate not found for EGAL"}


def test_delivery_returns_persisted_delivery_result():
    capability = Mock()
    record = make_record(AlertDeliveryStatus.DELIVERED)
    capability.execute.return_value = record
    app = create_app(
        InMemoryAnalysisResultStore(),
        deliver_alert_by_symbol=capability,
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/alerts/EGAL/deliver?channel=telegram")

    assert response.status_code == 200
    assert response.json() == {
        "stock_id": str(record.stock_id),
        "snapshot_id": str(record.snapshot_id),
        "channel": "telegram",
        "status": "delivered",
        "last_error": None,
    }
    capability.execute.assert_called_once_with("EGAL", "telegram")


def test_delivery_returns_failed_outcome_without_transport_error():
    capability = Mock()
    record = make_record(AlertDeliveryStatus.FAILED)
    capability.execute.return_value = record
    app = create_app(
        InMemoryAnalysisResultStore(),
        deliver_alert_by_symbol=capability,
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/alerts/EGAL/deliver?channel=telegram")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["last_error"] == "provider unavailable"


def test_delivery_does_not_construct_or_recalculate_an_alert():
    capability = Mock()
    record = make_record(AlertDeliveryStatus.DELIVERED)
    capability.execute.return_value = record
    app = create_app(
        InMemoryAnalysisResultStore(),
        deliver_alert_by_symbol=capability,
    )

    with TestClient(app) as client:
        client.post("/api/v1/alerts/EGAL/deliver?channel=telegram")

    capability.execute.assert_called_once_with("EGAL", "telegram")
