from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Protocol
from uuid import UUID, uuid4

from app.domain.signals.outcome import SignalOutcomeRecord
from app.domain.signals.outcome_event import (
    OutcomeCorrectionDecision,
    OutcomeEvent,
    OutcomeEventKind,
)


class OutcomeEventStore(Protocol):
    def record_initial(
        self, outcome: SignalOutcomeRecord, *, actor_id: str, idempotency_key: str,
        actor_credential_id: UUID | None = None,
    ) -> OutcomeEvent: ...

    def submit_correction(
        self,
        outcome: SignalOutcomeRecord,
        *,
        supersedes_event_id: UUID,
        actor_id: str,
        idempotency_key: str,
        actor_credential_id: UUID | None = None,
    ) -> OutcomeEvent: ...

    def review_correction(
        self,
        correction_event_id: UUID,
        *,
        reviewer_id: str,
        decision: OutcomeCorrectionDecision,
        idempotency_key: str,
        reviewer_credential_id: UUID | None = None,
    ) -> OutcomeEvent: ...

    def outcome_as_of(
        self, signal_id: UUID, *, cutoff: datetime
    ) -> OutcomeEvent | None: ...

    def events_for(self, signal_id: UUID) -> tuple[OutcomeEvent, ...]: ...


class InMemoryOutcomeEventStore:
    """Append-only reference implementation with knowledge-time reconstruction."""

    def __init__(
        self, *, clock: Callable[[], datetime] | None = None
    ) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._events: list[OutcomeEvent] = []
        self._idempotency: dict[str, OutcomeEvent] = {}

    def _append(
        self,
        *,
        signal_id: UUID,
        kind: OutcomeEventKind,
        actor_id: str,
        idempotency_key: str,
        outcome: SignalOutcomeRecord | None = None,
        supersedes_event_id: UUID | None = None,
        decision: OutcomeCorrectionDecision | None = None,
        actor_credential_id: UUID | None = None,
    ) -> OutcomeEvent:
        key = idempotency_key.strip()
        if not key:
            raise ValueError("idempotency_key is required")
        existing = self._idempotency.get(key)
        candidate = (
            signal_id, kind, actor_id.strip(), outcome, supersedes_event_id,
            decision, actor_credential_id,
        )
        if existing is not None:
            actual = (
                existing.signal_id, existing.kind, existing.actor_id,
                existing.outcome, existing.supersedes_event_id, existing.decision,
                existing.actor_credential_id,
            )
            if actual != candidate:
                raise ValueError("idempotency key reused with different outcome event")
            return existing

        timestamp = self._clock()
        event = OutcomeEvent(
            event_id=uuid4(),
            signal_id=signal_id,
            kind=kind,
            recorded_at=timestamp,
            actor_id=actor_id.strip(),
            idempotency_key=key,
            outcome=outcome,
            supersedes_event_id=supersedes_event_id,
            decision=decision,
            actor_credential_id=actor_credential_id,
        )
        self._events.append(event)
        self._idempotency[key] = event
        return event

    def record_initial(
        self,
        outcome: SignalOutcomeRecord,
        *,
        actor_id: str,
        idempotency_key: str,
        actor_credential_id: UUID | None = None,
    ) -> OutcomeEvent:
        if idempotency_key.strip() in self._idempotency:
            return self._append(
                signal_id=outcome.signal_id,
                kind=OutcomeEventKind.OUTCOME_RECORDED,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                outcome=outcome,
                actor_credential_id=actor_credential_id,
            )
        if any(
            event.signal_id == outcome.signal_id
            and event.kind is OutcomeEventKind.OUTCOME_RECORDED
            for event in self._events
        ):
            raise ValueError("initial outcome already recorded for signal")
        return self._append(
            signal_id=outcome.signal_id,
            kind=OutcomeEventKind.OUTCOME_RECORDED,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            outcome=outcome,
            actor_credential_id=actor_credential_id,
        )

    def submit_correction(
        self,
        outcome: SignalOutcomeRecord,
        *,
        supersedes_event_id: UUID,
        actor_id: str,
        idempotency_key: str,
        actor_credential_id: UUID | None = None,
    ) -> OutcomeEvent:
        if idempotency_key.strip() in self._idempotency:
            return self._append(
                signal_id=outcome.signal_id,
                kind=OutcomeEventKind.CORRECTION_SUBMITTED,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                outcome=outcome,
                supersedes_event_id=supersedes_event_id,
                actor_credential_id=actor_credential_id,
            )
        current = self.outcome_as_of(outcome.signal_id, cutoff=self._clock())
        if current is None or current.event_id != supersedes_event_id:
            raise ValueError("correction must supersede the current accepted outcome")
        if any(
            event.signal_id == outcome.signal_id
            and event.kind is OutcomeEventKind.CORRECTION_SUBMITTED
            and not self._has_review(event.event_id)
            for event in self._events
        ):
            raise ValueError("an outcome correction is already awaiting review")
        return self._append(
            signal_id=outcome.signal_id,
            kind=OutcomeEventKind.CORRECTION_SUBMITTED,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            outcome=outcome,
            supersedes_event_id=supersedes_event_id,
            actor_credential_id=actor_credential_id,
        )

    def review_correction(
        self,
        correction_event_id: UUID,
        *,
        reviewer_id: str,
        decision: OutcomeCorrectionDecision,
        idempotency_key: str,
        reviewer_credential_id: UUID | None = None,
    ) -> OutcomeEvent:
        if idempotency_key.strip() in self._idempotency:
            correction = next(
                (event for event in self._events if event.event_id == correction_event_id),
                None,
            )
            if correction is None:
                raise ValueError("outcome correction does not exist")
            return self._append(
                signal_id=correction.signal_id,
                kind=OutcomeEventKind.CORRECTION_REVIEWED,
                actor_id=reviewer_id,
                idempotency_key=idempotency_key,
                supersedes_event_id=correction_event_id,
                decision=decision,
                actor_credential_id=reviewer_credential_id,
            )
        correction = next(
            (
                event for event in self._events
                if event.event_id == correction_event_id
                and event.kind is OutcomeEventKind.CORRECTION_SUBMITTED
            ),
            None,
        )
        if correction is None:
            raise ValueError("outcome correction does not exist")
        if correction.actor_id == reviewer_id.strip():
            raise ValueError("correction author cannot review their own correction")
        if (
            correction.actor_credential_id is not None
            and correction.actor_credential_id == reviewer_credential_id
        ):
            raise ValueError("correction author credential cannot review its own correction")
        if correction.actor_credential_id is not None and reviewer_credential_id is None:
            raise ValueError("independent reviewer credential is required")
        if self._has_review(correction_event_id):
            raise ValueError("outcome correction has already been reviewed")
        return self._append(
            signal_id=correction.signal_id,
            kind=OutcomeEventKind.CORRECTION_REVIEWED,
            actor_id=reviewer_id,
            idempotency_key=idempotency_key,
            supersedes_event_id=correction_event_id,
            decision=decision,
            actor_credential_id=reviewer_credential_id,
        )

    def _has_review(self, correction_event_id: UUID) -> bool:
        return any(
            event.kind is OutcomeEventKind.CORRECTION_REVIEWED
            and event.supersedes_event_id == correction_event_id
            for event in self._events
        )

    def outcome_as_of(
        self, signal_id: UUID, *, cutoff: datetime
    ) -> OutcomeEvent | None:
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("cutoff must be timezone-aware")
        eligible = [
            event for event in self._events
            if event.signal_id == signal_id and event.recorded_at <= cutoff
        ]
        initial = next(
            (event for event in eligible if event.kind is OutcomeEventKind.OUTCOME_RECORDED),
            None,
        )
        if initial is None:
            return None
        current = initial
        corrections = [
            event for event in eligible
            if event.kind is OutcomeEventKind.CORRECTION_SUBMITTED
        ]
        for correction in corrections:
            review = next(
                (
                    event for event in eligible
                    if event.kind is OutcomeEventKind.CORRECTION_REVIEWED
                    and event.supersedes_event_id == correction.event_id
                ),
                None,
            )
            if (
                review is not None
                and review.decision is OutcomeCorrectionDecision.ACCEPTED
                and correction.supersedes_event_id == current.event_id
            ):
                current = correction
        return current

    def events_for(self, signal_id: UUID) -> tuple[OutcomeEvent, ...]:
        return tuple(event for event in self._events if event.signal_id == signal_id)
