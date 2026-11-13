from __future__ import annotations

from uuid import UUID

from app.application.security.identity import AuthenticatedIdentity
from app.application.signals.outcome_event_store import OutcomeEventStore
from app.domain.identity.user import UserStatus
from app.domain.signals.outcome import SignalOutcomeRecord
from app.domain.signals.outcome_event import (
    OutcomeCorrectionDecision,
    OutcomeEvent,
    OutcomeEventKind,
)


class OutcomeCorrectionService:
    """Authenticated application boundary for outcome corrections and reviews."""

    def __init__(self, events: OutcomeEventStore) -> None:
        self._events = events

    @staticmethod
    def _require_individual_credential(identity: AuthenticatedIdentity) -> tuple[str, UUID]:
        if (
            identity.user_id is None
            or identity.credential_id is None
            or identity.user_status is not UserStatus.ACTIVE
            or identity.subject != str(identity.user_id)
        ):
            raise ValueError("individually attributable active credential required")
        return identity.subject, identity.credential_id

    def events_for(self, signal_id: UUID) -> tuple[OutcomeEvent, ...]:
        return self._events.events_for(signal_id)

    def submit_correction(
        self,
        signal_id: UUID,
        outcome: SignalOutcomeRecord,
        *,
        supersedes_event_id: UUID,
        identity: AuthenticatedIdentity,
        idempotency_key: str,
    ) -> OutcomeEvent:
        actor_id, credential_id = self._require_individual_credential(identity)
        if outcome.signal_id != signal_id:
            raise ValueError("outcome signal identity mismatch")
        if not idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        return self._events.submit_correction(
            outcome,
            supersedes_event_id=supersedes_event_id,
            actor_id=actor_id,
            actor_credential_id=credential_id,
            idempotency_key=idempotency_key,
        )

    def review_correction(
        self,
        signal_id: UUID,
        correction_event_id: UUID,
        *,
        identity: AuthenticatedIdentity,
        decision: OutcomeCorrectionDecision,
        idempotency_key: str,
    ) -> OutcomeEvent:
        reviewer_id, credential_id = self._require_individual_credential(identity)
        correction = next(
            (
                event for event in self._events.events_for(signal_id)
                if event.event_id == correction_event_id
                and event.kind is OutcomeEventKind.CORRECTION_SUBMITTED
            ),
            None,
        )
        if correction is None:
            raise ValueError("outcome correction does not exist for signal")
        if not idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        return self._events.review_correction(
            correction_event_id,
            reviewer_id=reviewer_id,
            reviewer_credential_id=credential_id,
            decision=decision,
            idempotency_key=idempotency_key,
        )
