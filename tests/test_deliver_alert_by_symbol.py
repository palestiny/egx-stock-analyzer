from uuid import uuid4
from unittest.mock import Mock

import pytest

from app.application.notifications.deliver_alert import DeliverAlert
from app.application.notifications.deliver_alert_by_symbol import (
    AlertCandidateNotFoundError,
    DeliverAlertBySymbol,
)
from app.application.notifications.delivery_store import (
    AlertDeliveryRecord,
    AlertDeliveryStatus,
)
from app.domain.reporting.alerts import AlertCandidate


def make_candidate() -> AlertCandidate:
    return AlertCandidate(
        stock_id=uuid4(),
        snapshot_id=uuid4(),
        classification="buy",
        stock_quality_score=7,
        entry_quality_score=3,
    )


def make_record(candidate: AlertCandidate, status: AlertDeliveryStatus) -> AlertDeliveryRecord:
    return AlertDeliveryRecord(
        stock_id=candidate.stock_id,
        snapshot_id=candidate.snapshot_id,
        channel="telegram",
        status=status,
        last_error=None if status is AlertDeliveryStatus.DELIVERED else "provider unavailable",
    )


def test_delivers_existing_candidate_by_symbol():
    candidate = make_candidate()
    get_candidate = Mock()
    get_candidate.execute.return_value = candidate
    deliver = Mock(spec=DeliverAlert)
    expected = make_record(candidate, AlertDeliveryStatus.DELIVERED)
    deliver.execute.return_value = expected

    result = DeliverAlertBySymbol(get_candidate, deliver).execute(" egal ", "telegram")

    assert result is expected
    get_candidate.execute.assert_called_once_with("EGAL")
    deliver.execute.assert_called_once_with(candidate, "telegram")


def test_missing_candidate_is_explicit():
    get_candidate = Mock()
    get_candidate.execute.return_value = None
    deliver = Mock(spec=DeliverAlert)

    with pytest.raises(
        AlertCandidateNotFoundError,
        match="Alert candidate not found for EGAL",
    ):
        DeliverAlertBySymbol(get_candidate, deliver).execute("EGAL", "telegram")

    deliver.execute.assert_not_called()


def test_empty_symbol_is_rejected_before_candidate_lookup():
    get_candidate = Mock()
    deliver = Mock(spec=DeliverAlert)

    with pytest.raises(ValueError, match="symbol cannot be empty"):
        DeliverAlertBySymbol(get_candidate, deliver).execute("  ", "telegram")

    get_candidate.execute.assert_not_called()
