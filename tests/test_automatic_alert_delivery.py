from unittest.mock import Mock
from uuid import uuid4

from app.application.notifications.automatic_alert_delivery import (
    AutomaticAlertDelivery,
    AutomaticAlertDeliveryState,
)
from app.application.notifications.delivery_store import (
    AlertDeliveryRecord,
    AlertDeliveryStatus,
)
from app.domain.execution import Execution
from app.domain.opportunity.classification import OpportunityClassification
from app.domain.reporting.alerts import AlertCandidate


def make_execution(*symbols: str) -> Execution:
    execution = Execution.create()
    execution.start()
    for symbol in symbols:
        execution.record_stock_success(symbol)
    execution.finish()
    return execution


def make_candidate():
    return AlertCandidate(
        stock_id=uuid4(),
        snapshot_id=uuid4(),
        classification=OpportunityClassification.BUY,
        stock_quality_score=8,
        entry_quality_score=7,
    )


def delivered():
    return AlertDeliveryRecord(
        stock_id=uuid4(),
        snapshot_id=uuid4(),
        channel="telegram",
        status=AlertDeliveryStatus.DELIVERED,
    )


def failed(reason="provider unavailable"):
    return AlertDeliveryRecord(
        stock_id=uuid4(),
        snapshot_id=uuid4(),
        channel="telegram",
        status=AlertDeliveryStatus.FAILED,
        last_error=reason,
    )


def test_no_candidates_is_completed_no_op():
    get_candidate = Mock(return_value=None)
    deliver = Mock()
    policy = AutomaticAlertDelivery(get_candidate, deliver)

    result = policy.execute(make_execution("EGAL"))

    assert result.state is AutomaticAlertDeliveryState.COMPLETED
    assert result.attempted_count == 0
    assert result.delivered_count == 0
    assert result.skipped_count == 1
    assert result.failed_count == 0
    deliver.execute.assert_not_called()


def test_multiple_candidates_are_delivered_in_deterministic_symbol_order():
    get_candidate = Mock(side_effect=lambda symbol: make_candidate())
    deliver = Mock(side_effect=lambda candidate, channel: delivered())
    policy = AutomaticAlertDelivery(get_candidate, deliver)

    result = policy.execute(make_execution("SVCE", "EGAL", "IEEC"))

    assert result.state is AutomaticAlertDeliveryState.COMPLETED
    assert [call.args[0] for call in get_candidate.call_args_list] == ["EGAL", "IEEC", "SVCE"]
    assert deliver.call_count == 3


def test_one_delivery_failure_does_not_stop_later_candidates():
    get_candidate = Mock(side_effect=lambda symbol: make_candidate())
    deliver = Mock(side_effect=[failed(), delivered()])
    policy = AutomaticAlertDelivery(get_candidate, deliver)

    result = policy.execute(make_execution("EGAL", "IEEC"))

    assert result.state is AutomaticAlertDeliveryState.COMPLETED_WITH_ERRORS
    assert result.attempted_count == 2
    assert result.delivered_count == 1
    assert result.failed_count == 1
    assert result.failure_reasons == {"EGAL": "provider unavailable"}
    assert deliver.call_count == 2


def test_all_delivery_failures_return_failed():
    get_candidate = Mock(return_value=make_candidate())
    deliver = Mock(return_value=failed("telegram failed"))
    policy = AutomaticAlertDelivery(get_candidate, deliver)

    result = policy.execute(make_execution("EGAL", "IEEC"))

    assert result.state is AutomaticAlertDeliveryState.FAILED
    assert result.attempted_count == 2
    assert result.delivered_count == 0
    assert result.failed_count == 2
    assert result.failure_reasons == {
        "EGAL": "telegram failed",
        "IEEC": "telegram failed",
    }


def test_repeated_execution_delegates_idempotency_to_deliver_alert():
    candidate = make_candidate()
    get_candidate = Mock(return_value=candidate)
    deliver = Mock(return_value=delivered())
    policy = AutomaticAlertDelivery(get_candidate, deliver)
    execution = make_execution("EGAL")

    policy.execute(execution)
    policy.execute(execution)

    assert deliver.call_count == 2
    assert all(call.args[1] == "telegram" for call in deliver.call_args_list)


def test_analysis_execution_is_not_mutated():
    get_candidate = Mock(return_value=None)
    deliver = Mock()
    policy = AutomaticAlertDelivery(get_candidate, deliver)
    execution = make_execution("EGAL", "IEEC")
    original_id = execution.id
    original_successes = set(execution.successful_stock_ids)
    original_failures = set(execution.failed_stock_ids)

    policy.execute(execution)

    assert execution.id == original_id
    assert execution.successful_stock_ids == original_successes
    assert execution.failed_stock_ids == original_failures
