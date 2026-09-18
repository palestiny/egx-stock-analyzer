from uuid import uuid4

from app.application.notifications.delivery_store import AlertDeliveryStatus
from app.application.notifications.deliver_alert import DeliverAlert
from app.domain.reporting.alerts import AlertCandidate
from app.infrastructure.notifications.sqlite_alert_delivery_store import SQLiteAlertDeliveryStore


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    def send(self, candidate, channel) -> None:
        self.calls += 1


def candidate() -> AlertCandidate:
    return AlertCandidate(
        stock_id=uuid4(),
        snapshot_id=uuid4(),
        classification="buy",
        stock_quality_score=8,
        entry_quality_score=3,
    )


def test_sqlite_delivery_state_survives_store_recreation(tmp_path):
    path = tmp_path / "alerts.db"
    first_store = SQLiteAlertDeliveryStore(str(path))
    provider = FakeProvider()
    item = candidate()

    result = DeliverAlert(first_store, provider).execute(item, "test")

    assert result.status is AlertDeliveryStatus.DELIVERED
    second_store = SQLiteAlertDeliveryStore(str(path))
    restored = second_store.get(item.stock_id, item.snapshot_id, "test")

    assert restored is not None
    assert restored.status is AlertDeliveryStatus.DELIVERED


def test_sqlite_delivery_is_idempotent_after_store_recreation(tmp_path):
    path = tmp_path / "alerts.db"
    item = candidate()
    first_provider = FakeProvider()
    DeliverAlert(SQLiteAlertDeliveryStore(str(path)), first_provider).execute(item, "test")

    second_provider = FakeProvider()
    result = DeliverAlert(SQLiteAlertDeliveryStore(str(path)), second_provider).execute(item, "test")

    assert result.status is AlertDeliveryStatus.DELIVERED
    assert second_provider.calls == 0