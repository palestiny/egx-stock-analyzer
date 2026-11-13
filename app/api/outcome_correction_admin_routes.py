from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.application.security.identity import AuthenticatedIdentity
from app.application.signals.outcome_correction_service import OutcomeCorrectionService
from app.domain.signals.model import SignalDirection
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord
from app.domain.signals.outcome_event import OutcomeCorrectionDecision, OutcomeEvent


class OutcomeCorrectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supersedes_event_id: UUID
    idempotency_key: str = Field(min_length=1, max_length=200)
    symbol: str = Field(min_length=1, max_length=32)
    outcome: Literal["TARGET_HIT", "INVALIDATED"]
    direction: Literal["BUY", "SELL"]
    observed_at: datetime
    entry_price: Decimal
    exit_price: Decimal
    realized_return: Decimal
    realized_r: Decimal
    invalidation: Decimal
    target_label: str | None = None
    strategy_id: str = Field(min_length=1, max_length=200)
    strategy_version: str = Field(min_length=1, max_length=100)
    data_timestamp: datetime


class OutcomeCorrectionReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["ACCEPTED", "REJECTED"]
    idempotency_key: str = Field(min_length=1, max_length=200)


def _event_payload(event: OutcomeEvent) -> dict[str, object]:
    outcome = event.outcome
    return {
        "event_id": str(event.event_id),
        "signal_id": str(event.signal_id),
        "kind": event.kind.value,
        "recorded_at": event.recorded_at.isoformat(),
        "actor_id": event.actor_id,
        "actor_credential_id": (
            str(event.actor_credential_id) if event.actor_credential_id else None
        ),
        "idempotency_key": event.idempotency_key,
        "supersedes_event_id": (
            str(event.supersedes_event_id) if event.supersedes_event_id else None
        ),
        "decision": event.decision.value if event.decision else None,
        "outcome": (
            {
                "symbol": outcome.symbol,
                "outcome": outcome.outcome.value,
                "direction": outcome.direction.value,
                "observed_at": outcome.observed_at.isoformat(),
                "entry_price": str(outcome.entry_price),
                "exit_price": str(outcome.exit_price),
                "realized_return": str(outcome.realized_return),
                "realized_r": str(outcome.realized_r),
                "invalidation": str(outcome.invalidation),
                "target_label": outcome.target_label,
                "strategy_id": outcome.strategy_id,
                "strategy_version": outcome.strategy_version,
                "data_timestamp": outcome.data_timestamp.isoformat(),
            }
            if outcome else None
        ),
    }


def create_outcome_correction_admin_router(
    *,
    service: OutcomeCorrectionService | None,
    require_individual_operator,
) -> APIRouter:
    router = APIRouter()

    def configured_service() -> OutcomeCorrectionService:
        if service is None:
            raise HTTPException(
                status_code=503,
                detail="Outcome correction service is not configured",
            )
        return service

    @router.get("/api/v1/owner/signals/{signal_id}/outcome-events")
    def list_outcome_events(
        signal_id: UUID,
        _identity: AuthenticatedIdentity = Depends(require_individual_operator),
    ) -> dict[str, object]:
        return {
            "signal_id": str(signal_id),
            "events": [
                _event_payload(event)
                for event in configured_service().events_for(signal_id)
            ],
        }

    @router.post(
        "/api/v1/owner/signals/{signal_id}/outcome-corrections",
        status_code=201,
    )
    def submit_outcome_correction(
        signal_id: UUID,
        payload: OutcomeCorrectionPayload,
        identity: AuthenticatedIdentity = Depends(require_individual_operator),
    ) -> dict[str, object]:
        try:
            outcome = SignalOutcomeRecord(
                signal_id=signal_id,
                symbol=payload.symbol,
                outcome=SignalOutcome(payload.outcome),
                direction=SignalDirection(payload.direction),
                observed_at=payload.observed_at,
                entry_price=payload.entry_price,
                exit_price=payload.exit_price,
                realized_return=payload.realized_return,
                realized_r=payload.realized_r,
                invalidation=payload.invalidation,
                target_label=payload.target_label,
                strategy_id=payload.strategy_id,
                strategy_version=payload.strategy_version,
                data_timestamp=payload.data_timestamp,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        try:
            event = configured_service().submit_correction(
                signal_id,
                outcome,
                supersedes_event_id=payload.supersedes_event_id,
                identity=identity,
                idempotency_key=payload.idempotency_key,
            )
        except ValueError as error:
            message = str(error)
            status_code = 404 if "does not exist" in message else 409
            raise HTTPException(status_code=status_code, detail=message) from error
        return _event_payload(event)

    @router.post(
        "/api/v1/owner/signals/{signal_id}/outcome-corrections/{correction_event_id}/review",
        status_code=201,
    )
    def review_outcome_correction(
        signal_id: UUID,
        correction_event_id: UUID,
        payload: OutcomeCorrectionReviewPayload,
        identity: AuthenticatedIdentity = Depends(require_individual_operator),
    ) -> dict[str, object]:
        try:
            event = configured_service().review_correction(
                signal_id,
                correction_event_id,
                identity=identity,
                decision=OutcomeCorrectionDecision(payload.decision),
                idempotency_key=payload.idempotency_key,
            )
        except ValueError as error:
            message = str(error)
            status_code = 404 if "does not exist" in message else 409
            raise HTTPException(status_code=status_code, detail=message) from error
        return _event_payload(event)

    return router
