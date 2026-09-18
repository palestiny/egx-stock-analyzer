from uuid import uuid4

import pytest

from app.application.notifications.deliver_alert import DeliverAlert
from app.domain.reporting.alerts import AlertCandidate
from app.infrastructure.notifications.in_memory_alert_delivery_store import InMemoryAlertDeliveryStore


class FakeNotificationProvider:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.calls: list[tuple[AlertCandidate, str]] = []

    def send(self, candidate: AlertCandidate, channel: str) -> None:
        self.calls.append((candidate, channel))
        if self.failure is not None:
            raise self.failure


def make_candidate() -> AlertCandidate:
    return AlertCandidate(
        stock_id=uuid4(),
        snapshot_id=uuid4(),
        classification="buy",
        stock_quality_score=7,
        entry_quality_score=3,
    )


def test_new_alert_is_delivered_and_marked_delivered():
    store = InMemoryAlertDeliveryStore()
    provider = FakeNotificationProvider()
    use_case = DeliverAlert(store, provider)
    candidate = make_candidate()

    result = use_case.execute(candidate, "test")

    assert result.status.value == "delivered"
    assert provider.calls == [(candidate, "test")]
    record = store.get(candidate.stock_id, candidate.snapshot_id, "test")
    assert record is not None
    assert record.status.value == "delivered"


def test_duplicate_successful_delivery_is_idempotent():
    store = InMemoryAlertDeliveryStore()
    provider = FakeNotificationProvider()
    use_case = DeliverAlert(store, provider)
    candidate = make_candidate()

    first = use_case.execute(candidate, "test")
    second = use_case.execute(candidate, "test")

    assert first.status.value == "delivered"
    assert second.status.value == "delivered"
    assert provider.calls == [(candidate, "test")]


def test_provider_failure_records_failed_without_changing_candidate():
    store = InMemoryAlertDeliveryStore()
    provider = FakeNotificationProvider(RuntimeError("provider unavailable"))
    use_case = DeliverAlert(store, provider)
    candidate = make_candidate()

    result = use_case.execute(candidate, "test")

    assert result.status.value == "failed"
    assert result.last_error == "provider unavailable"
    assert candidate.stock_quality_score == 7
    assert candidate.entry_quality_score == 3


def test_one_failed_delivery_does_not_erase_another_success():
    store = InMemoryAlertDeliveryStore()
    success_provider = FakeNotificationProvider()
    failure_provider = FakeNotificationProvider(RuntimeError("down"))
    first = make_candidate()
    second = make_candidate()

    assert DeliverAlert(store, success_provider).execute(first, "test").status.value == "delivered"
    assert DeliverAlert(store, failure_provider).execute(second, "test").status.value == "failed"
    assert store.get(first.stock_id, first.snapshot_id, "test").status.value == "delivered"
    assert store.get(second.stock_id, second.snapshot_id, "test").status.value == "failed"


def test_alert_without_snapshot_identity_cannot_be_delivered():
    store = InMemoryAlertDeliveryStore()
    provider = FakeNotificationProvider()
    candidate = AlertCandidate(
        stock_id=uuid4(),
        snapshot_id=None,
        classification="buy",
        stock_quality_score=7,
        entry_quality_score=3,
    )

    with pytest.raises(ValueError, match="snapshot identity"):
        DeliverAlert(store, provider).execute(candidate, "test")
    assert provider.calls == []

def test_failed_delivery_is_not_retried_implicitly():
    store = InMemoryAlertDeliveryStore()
    failing_provider = FakeNotificationProvider(RuntimeError("down"))
    candidate = make_candidate()

    first = DeliverAlert(store, failing_provider).execute(candidate, "test")

    second_provider = FakeNotificationProvider()
    second = DeliverAlert(store, second_provider).execute(candidate, "test")

    assert first.status.value == "failed"
    assert second.status.value == "failed"
    assert second_provider.calls == []
