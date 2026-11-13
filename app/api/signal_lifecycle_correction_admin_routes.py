from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.application.security.identity import AuthenticatedIdentity
from app.application.signals.lifecycle_orchestrator import SignalLifecycleOrchestrator
from app.application.signals.lifecycle_unit_of_work import (
    LifecycleCorrectionRecord,
    LifecycleCorrectionReviewDecision,
)


class CorrectionReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["REJECTED", "ACCEPTED_NO_STATE_CHANGE", "REPLAY_REQUIRED"]
    reason: str = Field(min_length=1, max_length=1000)


def _correction_payload(record: LifecycleCorrectionRecord) -> dict[str, object]:
    bar = record.corrected_bar
    return {
        "correction_id": str(record.correction_id),
        "signal_id": str(record.signal_id),
        "original_identity": {
            "provider": record.original_identity[0],
            "symbol": record.original_identity[1],
            "timeframe": record.original_identity[2],
            "candle_at": record.original_identity[3].isoformat(),
            "revision": record.original_identity[4],
        },
        "corrected_bar": {
            "symbol": bar.symbol,
            "provider": bar.provider,
            "timeframe": bar.timeframe,
            "candle_at": bar.candle_at.isoformat(),
            "observed_at": bar.observed_at.isoformat(),
            "revision": bar.revision,
            "source_reference": bar.source_reference,
            "finality_attestation": bar.finality_attestation,
            "is_final": bar.is_final,
            "open": str(bar.open),
            "high": str(bar.high),
            "low": str(bar.low),
            "close": str(bar.close),
        },
        "operator_id": record.operator_id,
        "reason": record.reason,
        "calendar_version": record.calendar_version,
        "recorded_at": record.recorded_at.isoformat(),
        "status": record.status,
    }


def _review_payload(record: LifecycleCorrectionReviewDecision) -> dict[str, object]:
    return {
        "decision_id": str(record.decision_id),
        "correction_id": str(record.correction_id),
        "signal_id": str(record.signal_id),
        "decision": record.decision,
        "reviewer_id": record.reviewer_id,
        "reason": record.reason,
        "recorded_at": record.recorded_at.isoformat(),
    }


def create_signal_lifecycle_correction_admin_router(
    *,
    orchestrator: SignalLifecycleOrchestrator | None,
    require_operator,
) -> APIRouter:
    router = APIRouter()

    def configured_orchestrator() -> SignalLifecycleOrchestrator:
        if orchestrator is None:
            raise HTTPException(
                status_code=503,
                detail="Signal lifecycle correction review is not configured",
            )
        return orchestrator

    @router.get("/api/v1/owner/signals/{signal_id}/lifecycle-corrections")
    def list_lifecycle_corrections(
        signal_id: UUID,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        service = configured_orchestrator()
        corrections = service.lifecycle_corrections(signal_id)
        decisions = service.lifecycle_correction_review_decisions(signal_id)
        decisions_by_correction: dict[UUID, list[dict[str, object]]] = {}
        for decision in decisions:
            decisions_by_correction.setdefault(decision.correction_id, []).append(
                _review_payload(decision)
            )
        return {
            "signal_id": str(signal_id),
            "corrections": [
                {
                    **_correction_payload(correction),
                    "review_decisions": decisions_by_correction.get(
                        correction.correction_id, []
                    ),
                }
                for correction in corrections
            ],
        }

    @router.post(
        "/api/v1/owner/signals/{signal_id}/lifecycle-corrections/{correction_id}/review",
    @router.post(
        "/api/v1/owner/signals/{signal_id}/lifecycle-corrections/{correction_id}/rebuild",
        status_code=201,
    )
    def rebuild_lifecycle_correction(
        signal_id: UUID,
        correction_id: UUID,
        identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        service = configured_orchestrator()
        operator_id = identity.subject.strip()
        if not operator_id:
            raise HTTPException(status_code=403, detail="Attributable operator identity required")
        try:
            result = service.rebuild_daily_bar_correction(
                signal_id, correction_id, operator_id=operator_id,
                recorded_at=datetime.now(timezone.utc),
            )
        except ValueError as error:
            message = str(error)
            status_code = 404 if "does not exist" in message or "missing" in message else 409
            raise HTTPException(status_code=status_code, detail=message) from error
        return {
            "rebuild_id": str(result.rebuild_id),
            "correction_id": str(result.correction_id),
            "signal_id": str(result.signal_id),
            "previous_status": result.previous_status.value,
            "resulting_status": result.resulting_status.value,
            "observation_count": result.observation_count,
            "replay_digest": result.replay_digest,
            "superseded_event_id": str(result.superseded_event_id) if result.superseded_event_id else None,
            "correction_event_id": str(result.correction_event_id) if result.correction_event_id else None,
            "recorded_at": result.recorded_at.isoformat(),
        }

        status_code=201,
    )
    def review_lifecycle_correction(
        signal_id: UUID,
        correction_id: UUID,
        payload: CorrectionReviewPayload,
        identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        service = configured_orchestrator()
        reason = payload.reason.strip()
        if not reason:
            raise HTTPException(status_code=422, detail="review reason is required")
        # Audit time is assigned by the server; clients cannot backdate review events.
        recorded_at = datetime.now(timezone.utc)
        reviewer_id = identity.subject.strip()
        if not reviewer_id:
            raise HTTPException(status_code=403, detail="Attributable operator identity required")
        try:
            decision = service.record_daily_bar_correction_review(
                signal_id,
                correction_id,
                decision=payload.decision,
                reviewer_id=reviewer_id,
                reason=reason,
                recorded_at=recorded_at,
            )
        except ValueError as error:
            message = str(error)
            status_code = 404 if "does not exist" in message else 409
            raise HTTPException(status_code=status_code, detail=message) from error
        return _review_payload(decision)

    return router
