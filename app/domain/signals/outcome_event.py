from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.signals.outcome import SignalOutcomeRecord


class OutcomeEventKind(StrEnum):
    OUTCOME_RECORDED = "OUTCOME_RECORDED"
    CORRECTION_SUBMITTED = "CORRECTION_SUBMITTED"
    CORRECTION_REVIEWED = "CORRECTION_REVIEWED"


class OutcomeCorrectionDecision(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class OutcomeEvent:
    event_id: UUID
    signal_id: UUID
    kind: OutcomeEventKind
    recorded_at: datetime
    actor_id: str
    idempotency_key: str
    outcome: SignalOutcomeRecord | None = None
    supersedes_event_id: UUID | None = None
    decision: OutcomeCorrectionDecision | None = None
    actor_credential_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware")
        if not self.actor_id.strip():
            raise ValueError("actor_id is required")
        if not self.idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        if self.kind is OutcomeEventKind.OUTCOME_RECORDED:
            if self.outcome is None or self.supersedes_event_id is not None or self.decision is not None:
                raise ValueError("initial outcome event has an invalid shape")
        elif self.kind is OutcomeEventKind.CORRECTION_SUBMITTED:
            if self.outcome is None or self.supersedes_event_id is None or self.decision is not None:
                raise ValueError("outcome correction event has an invalid shape")
        elif self.kind is OutcomeEventKind.CORRECTION_REVIEWED:
            if self.outcome is not None or self.supersedes_event_id is None or self.decision is None:
                raise ValueError("outcome correction review event has an invalid shape")

        if self.outcome is not None and self.outcome.signal_id != self.signal_id:
            raise ValueError("outcome event signal identity mismatch")
