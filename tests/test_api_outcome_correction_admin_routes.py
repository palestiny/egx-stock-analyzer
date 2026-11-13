from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.application.signals.outcome_correction_service import OutcomeCorrectionService
from app.application.signals.outcome_event_store import InMemoryOutcomeEventStore
from app.domain.signals.model import SignalDirection
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord


def make_outcome(signal_id, *, exit_price="95"):
    observed = datetime(2026, 10, 10, 10, tzinfo=timezone.utc)
    return SignalOutcomeRecord(
        signal_id=signal_id,
        symbol="EGAL",
        outcome=SignalOutcome.INVALIDATED,
        direction=SignalDirection.BUY,
        observed_at=observed,
        entry_price=Decimal("100"),
        exit_price=Decimal(exit_price),
        realized_return=Decimal("-0.05"),
        realized_r=Decimal("-1"),
        invalidation=Decimal("95"),
        target_label=None,
        strategy_id="trend",
        strategy_version="1",
        data_timestamp=observed,
    )


def test_outcome_correction_routes_require_independent_active_credentials():
    events = InMemoryOutcomeEventStore()
    signal_id = uuid4()
    original = events.record_initial(
        make_outcome(signal_id),
        actor_id="system:signal-lifecycle",
        idempotency_key="initial",
    )
    service = OutcomeCorrectionService(events)
    author = AuthenticatedIdentity.user(
        uuid4(),
        credential_id=uuid4(),
        permissions=frozenset({Permission.OPERATOR}),
    )
    reviewer = AuthenticatedIdentity.user(
        uuid4(),
        credential_id=uuid4(),
        permissions=frozenset({Permission.OPERATOR}),
    )
    authenticator = Mock()
    authenticator.authenticate.side_effect = [author, reviewer]
    app = create_app(
        InMemoryAnalysisResultStore(),
        authenticator=authenticator,
        outcome_correction_service=service,
    )

    with TestClient(app) as client:
        submitted = client.post(
            f"/api/v1/owner/signals/{signal_id}/outcome-corrections",
            headers={"Authorization": "Bearer test"},
            json={
                "supersedes_event_id": str(original.event_id),
                "idempotency_key": "correction-1",
                "symbol": "EGAL",
                "outcome": "INVALIDATED",
                "direction": "BUY",
                "observed_at": "2026-10-10T10:00:00+00:00",
                "entry_price": "100",
                "exit_price": "96",
                "realized_return": "-0.04",
                "realized_r": "-0.8",
                "invalidation": "95",
                "target_label": None,
                "strategy_id": "trend",
                "strategy_version": "1",
                "data_timestamp": "2026-10-10T10:00:00+00:00",
            },
        )
        assert submitted.status_code == 201
        correction_id = submitted.json()["event_id"]
        reviewed = client.post(
            f"/api/v1/owner/signals/{signal_id}/outcome-corrections/{correction_id}/review",
            headers={"Authorization": "Bearer test"},
            json={
                "decision": "ACCEPTED",
                "idempotency_key": "review-1",
            },
        )

    assert reviewed.status_code == 201
    assert reviewed.json()["actor_id"] == reviewer.subject
    assert reviewed.json()["actor_credential_id"] == str(reviewer.credential_id)
    assert events.outcome_as_of(signal_id, cutoff=datetime.now(timezone.utc)).event_id.hex == correction_id.replace("-", "")


def test_outcome_correction_routes_reject_legacy_operator_without_individual_credential():
    events = InMemoryOutcomeEventStore()
    service = OutcomeCorrectionService(events)
    app = create_app(
        InMemoryAnalysisResultStore(),
        operator_token="legacy-token",
        outcome_correction_service=service,
    )
    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/owner/signals/{uuid4()}/outcome-events",
            headers={"Authorization": "Bearer legacy-token"},
        )
    assert response.status_code == 403
