from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from app.application.alerts.in_memory import InMemoryAlertPublisher
from app.application.alerts.ports import AlertPublisher
from app.application.alerts.signal_snapshot import snapshot_signal
from app.application.market_data.completed_daily_bar_source import ProviderDailyBarEvidence
from app.application.signals.lifecycle_unit_of_work import (
    LifecycleBootstrapRecord,
    LifecycleCorrectionRecord,
    LifecycleCorrectionReviewDecision,
    LifecycleCorrectionRebuildRecord,
    LifecycleSessionGapEvent,
    LifecycleObservationRecord,
    InMemorySignalLifecycleUnitOfWork,
    SignalLifecycleTransaction,
    SignalLifecycleUnitOfWork,
)
from app.application.signals.store import InMemorySignalHistoryStore, SignalHistoryStore
from app.application.signals.track_record import InMemoryTrackRecordStore, TrackRecordStore
from app.domain.alerts.model import AlertEvent, AlertEventType
from app.domain.signals.lifecycle import (
    CompletedDailyBarObservation,
    SignalMarketState,
    transition_signal,
    transition_signal_from_completed_daily_bar,
)
from app.domain.signals.model import Signal, SignalDirection, SignalStatus
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord


@dataclass(frozen=True)
class SignalLifecycleResult:
    signal_id: UUID
    signal: Signal
    changed: bool
    outcome_recorded: bool
    alert_published: bool


class SignalLifecycleOrchestrator:
    """Coordinate a lifecycle observation through one atomic persistence boundary."""

    def __init__(
        self,
        history: SignalHistoryStore,
        alerts: AlertPublisher,
        track_record: TrackRecordStore,
        *,
        unit_of_work: SignalLifecycleUnitOfWork | None = None,
    ) -> None:
        if unit_of_work is None:
            if not (
                isinstance(history, InMemorySignalHistoryStore)
                and isinstance(alerts, InMemoryAlertPublisher)
                and isinstance(track_record, InMemoryTrackRecordStore)
            ):
                raise ValueError(
                    "durable lifecycle stores require an explicit atomic unit of work"
                )
            unit_of_work = InMemorySignalLifecycleUnitOfWork(
                history, alerts, track_record
            )
        self._unit_of_work = unit_of_work

    def _execute_in_transaction(
        self,
        operation,
        transaction: SignalLifecycleTransaction | None,
    ):
        if transaction is not None:
            return operation(transaction)
        return self._unit_of_work.execute(operation)

    def bootstrap_records(
        self,
        signal_id: UUID,
        *,
        transaction: SignalLifecycleTransaction | None = None,
    ) -> tuple[LifecycleBootstrapRecord, ...]:
        return self._execute_in_transaction(
            lambda current: current.bootstrap_records(signal_id), transaction
        )

    def process(
        self,
        signal: Signal,
        state: SignalMarketState,
        *,
        entry_price: Decimal,
    ) -> SignalLifecycleResult:
        if not entry_price.is_finite() or entry_price <= 0:
            raise ValueError("entry price must be finite and positive")
        if state.observed_at < signal.generated_at:
            raise ValueError("market observation cannot precede signal generation")

        def persist(transaction: SignalLifecycleTransaction) -> SignalLifecycleResult:
            latest = transaction.latest_for_identity(
                signal.symbol,
                signal.strategy_id,
                signal.strategy_version,
                signal.generated_at,
            )
            if (
                latest is not None
                and latest.signal.strategy_id == signal.strategy_id
                and latest.signal.strategy_version == signal.strategy_version
                and latest.signal.generated_at == signal.generated_at
            ):
                signal_id = latest.signal_id
                current = latest.signal
            else:
                created = transaction.record_signal(
                    signal, "CREATED", signal.generated_at
                )
                signal_id = created.signal_id
                current = signal

            transitioned = transition_signal(current, state)
            if transitioned.status is current.status:
                return SignalLifecycleResult(
                    signal_id=signal_id,
                    signal=current,
                    changed=False,
                    outcome_recorded=False,
                    alert_published=False,
                )

            outcome = None
            if transitioned.status in (
                SignalStatus.TRIGGERED,
                SignalStatus.INVALIDATED,
            ):
                outcome = self._build_outcome(
                    signal_id, transitioned, state, entry_price
                )

            event = self._build_alert(
                signal_id, transitioned, state.observed_at
            )
            transaction.record_signal(
                transitioned,
                f"STATUS_{transitioned.status.value}",
                state.observed_at,
                signal_id=signal_id,
            )
            if outcome is not None:
                transaction.record_outcome(outcome)
            transaction.publish_alert(event)
            return SignalLifecycleResult(
                signal_id=signal_id,
                signal=transitioned,
                changed=True,
                outcome_recorded=outcome is not None,
                alert_published=True,
            )

        return self._unit_of_work.execute(persist)

    @staticmethod
    def _same_provider_evidence_identity(
        existing: ProviderDailyBarEvidence | None,
        incoming: ProviderDailyBarEvidence | None,
    ) -> bool:
        if existing is None or incoming is None:
            return existing is incoming
        return (
            existing.provider_id == incoming.provider_id
            and existing.provider_contract_version == incoming.provider_contract_version
            and existing.instrument_symbol == incoming.instrument_symbol
            and existing.session_date == incoming.session_date
            and existing.source_timestamp == incoming.source_timestamp
        )

    def process_completed_daily_bar(
        self,
        signal_id: UUID,
        bar: CompletedDailyBarObservation,
        *,
        calendar_version: str,
        policy_version: str = "dec138-daily-ohlc-v1",
        resolved_gap_session_date: date | None = None,
        resolved_gap_at: datetime | None = None,
        provider_evidence: ProviderDailyBarEvidence | None = None,
        transaction: SignalLifecycleTransaction | None = None,
    ) -> SignalLifecycleResult | None:
        """Evaluate one provider-attested completed candle for a published signal.

        This path records market-level evidence only. It never invents an entry
        fill or creates realized return/R accounting.
        """
        if provider_evidence is not None and provider_evidence.bar != bar:
            raise ValueError("provider evidence bar must match the lifecycle bar")
        if not policy_version or not policy_version.strip():
            raise ValueError("policy_version is required")
        if not calendar_version or not calendar_version.strip():
            raise ValueError("calendar_version is required")
        if resolved_gap_at is not None and (
            resolved_gap_at.tzinfo is None or resolved_gap_at.utcoffset() is None
        ):
            raise ValueError("resolved_gap_at must be timezone-aware")

        def persist(transaction: SignalLifecycleTransaction) -> SignalLifecycleResult | None:
            latest = transaction.latest_for_signal(signal_id)
            if latest is None:
                return None
            if latest.signal.symbol.strip().upper() != bar.symbol.strip().upper():
                raise ValueError("daily candle symbol does not match opportunity")
            if latest.event not in {
                "PUBLISHED",
                "PUBLISHED_VERSION",
                "STATUS_TRIGGERED",
                "STATUS_INVALIDATED",
                "STATUS_EXPIRED",
                "STATUS_CLOSED",
                "EVIDENCE_CHANGED_INVALIDATED",
            } and not latest.event.startswith("CORRECTION_REPLAY_REBUILT:"):
                return None
            if latest.signal.status is not SignalStatus.ACTIVE:
                return SignalLifecycleResult(
                    signal_id=latest.signal_id,
                    signal=latest.signal,
                    changed=False,
                    outcome_recorded=False,
                    alert_published=False,
                )

            existing = transaction.get_observation(signal_id, bar.identity)
            if existing is not None:
                previous = existing.bar
                same_source_payload = (
                    previous.symbol.strip().upper() == bar.symbol.strip().upper()
                    and previous.provider.strip().casefold() == bar.provider.strip().casefold()
                    and previous.timeframe.strip().upper() == bar.timeframe.strip().upper()
                    and previous.candle_at == bar.candle_at
                    and previous.revision.strip() == bar.revision.strip()
                    and previous.source_reference == bar.source_reference
                    and previous.finality_attestation == bar.finality_attestation
                    and previous.is_final == bar.is_final
                    and previous.open == bar.open
                    and previous.high == bar.high
                    and previous.low == bar.low
                    and previous.close == bar.close
                    and existing.policy_version == policy_version.strip()
                    and existing.calendar_version == calendar_version.strip()
                    and self._same_provider_evidence_identity(
                        existing.provider_evidence, provider_evidence
                    )
                )
                if not same_source_payload or existing.signal_id != signal_id:
                    raise ValueError(
                        "conflicting replay for completed daily candle identity; "
                        "a correction requires a new revision and explicit reconciliation"
                    )
                return SignalLifecycleResult(
                    signal_id=latest.signal_id,
                    signal=latest.signal,
                    changed=False,
                    outcome_recorded=False,
                    alert_published=False,
                )

            corrections = transaction.corrections(signal_id)
            review_decisions = transaction.correction_review_decisions(signal_id)
            latest_decision_by_correction: dict[UUID, LifecycleCorrectionReviewDecision] = {}
            for decision in review_decisions:
                latest_decision_by_correction[decision.correction_id] = decision
            completed_rebuild_ids = {item.correction_id for item in transaction.correction_rebuilds(signal_id)}
            unresolved_corrections = [
                correction
                for correction in corrections
                if (
                    correction.correction_id not in latest_decision_by_correction
                    or (
                        latest_decision_by_correction[correction.correction_id].decision == "REPLAY_REQUIRED"
                        and correction.correction_id not in completed_rebuild_ids
                    )
                    or latest_decision_by_correction[correction.correction_id].decision
                    not in {"REJECTED", "ACCEPTED_NO_STATE_CHANGE", "REPLAY_REQUIRED"}
                )
            ]
            if unresolved_corrections:
                raise ValueError(
                    "unresolved daily-bar correction review blocks lifecycle progression"
                )

            previous_observation = transaction.latest_observation(latest.signal_id)
            if previous_observation is not None:
                previous_bar = previous_observation.bar
                if bar.candle_at < previous_bar.candle_at:
                    raise ValueError("out-of-order daily candle cannot advance lifecycle")
                if bar.candle_at == previous_bar.candle_at:
                    raise ValueError(
                        "same-session correction requires explicit reconciliation"
                    )

            current = latest.signal
            transitioned = transition_signal_from_completed_daily_bar(current, bar)
            transaction.record_observation(
                LifecycleObservationRecord(
                    signal_id=latest.signal_id,
                    bar=bar,
                    policy_version=policy_version.strip(),
                    calendar_version=calendar_version.strip(),
                    resulting_status=transitioned.status,
                    provider_evidence=provider_evidence,
                )
            )
            if resolved_gap_session_date is not None:
                matching_gaps = [
                    event
                    for event in transaction.session_gap_events(signal_id)
                    if event.session_date == resolved_gap_session_date
                    and event.calendar_version == calendar_version.strip()
                ]
                if matching_gaps and matching_gaps[-1].status == "STALE":
                    previous_gap = matching_gaps[-1]
                    transaction.record_session_gap_event(
                        LifecycleSessionGapEvent(
                            event_id=uuid5(
                                NAMESPACE_URL,
                                f"{previous_gap.gap_id}:RESOLVED:ELIGIBLE_BAR_RECONCILED",
                            ),
                            gap_id=previous_gap.gap_id,
                            signal_id=signal_id,
                            session_date=resolved_gap_session_date,
                            calendar_version=calendar_version.strip(),
                            status="RESOLVED",
                            reason="ELIGIBLE_BAR_RECONCILED",
                            recorded_at=resolved_gap_at or bar.observed_at,
                        )
                    )
            if transitioned.status is current.status:
                return SignalLifecycleResult(
                    signal_id=latest.signal_id,
                    signal=current,
                    changed=False,
                    outcome_recorded=False,
                    alert_published=False,
                )

            event_type = (
                AlertEventType.SIGNAL_TRIGGERED
                if transitioned.status is SignalStatus.TRIGGERED
                else AlertEventType.SIGNAL_INVALIDATED
            )
            event_id = uuid5(
                NAMESPACE_URL,
                f"signal-daily-bar:{latest.signal_id}:{bar.identity!r}:{policy_version.strip()}:{calendar_version.strip()}",
            )
            transaction.record_signal(
                transitioned,
                f"STATUS_{transitioned.status.value}",
                bar.observed_at,
                signal_id=latest.signal_id,
            )
            transaction.publish_alert(
                AlertEvent(
                    event_id=event_id,
                    signal_id=latest.signal_id,
                    symbol=transitioned.symbol,
                    event_type=event_type,
                    occurred_at=bar.observed_at,
                    message=(
                        f"{transitioned.symbol} opportunity "
                        f"{transitioned.status.value.lower()} from completed daily candle"
                    ),
                    signal_snapshot=snapshot_signal(transitioned),
                )
            )
            return SignalLifecycleResult(
                signal_id=latest.signal_id,
                signal=transitioned,
                changed=True,
                outcome_recorded=False,
                alert_published=True,
            )

        return self._execute_in_transaction(persist, transaction)

    def mark_session_gap(
        self,
        signal_id: UUID,
        *,
        session_date: date,
        calendar_version: str,
        reason: str,
        detected_at: datetime,
        transaction: SignalLifecycleTransaction | None = None,
    ) -> LifecycleSessionGapEvent:
        if not calendar_version.strip() or not reason.strip():
            raise ValueError("calendar_version and gap reason are required")
        if detected_at.tzinfo is None or detected_at.utcoffset() is None:
            raise ValueError("detected_at must be timezone-aware")
        gap_id = uuid5(
            NAMESPACE_URL,
            f"signal-session-gap:{signal_id}:{session_date.isoformat()}:{calendar_version.strip()}",
        )
        event = LifecycleSessionGapEvent(
            event_id=uuid5(NAMESPACE_URL, f"{gap_id}:STALE:{reason.strip()}"),
            gap_id=gap_id,
            signal_id=signal_id,
            session_date=session_date,
            calendar_version=calendar_version.strip(),
            status="STALE",
            reason=reason.strip(),
            recorded_at=detected_at,
        )

        def persist(transaction: SignalLifecycleTransaction) -> LifecycleSessionGapEvent:
            if transaction.latest_for_signal(signal_id) is None:
                raise ValueError("opportunity identity does not exist")
            transaction.record_session_gap_event(event)
            return event

        return self._execute_in_transaction(persist, transaction)

    def resolve_session_gap(
        self,
        signal_id: UUID,
        *,
        session_date: date,
        calendar_version: str,
        reason: str,
        resolved_at: datetime,
        transaction: SignalLifecycleTransaction | None = None,
    ) -> LifecycleSessionGapEvent | None:
        if not calendar_version.strip() or not reason.strip():
            raise ValueError("calendar_version and resolution reason are required")
        if resolved_at.tzinfo is None or resolved_at.utcoffset() is None:
            raise ValueError("resolved_at must be timezone-aware")

        def persist(transaction: SignalLifecycleTransaction) -> LifecycleSessionGapEvent | None:
            matches = [
                event for event in transaction.session_gap_events(signal_id)
                if event.session_date == session_date
                and event.calendar_version == calendar_version.strip()
            ]
            if not matches or matches[-1].status != "STALE":
                return None
            previous = matches[-1]
            resolved = LifecycleSessionGapEvent(
                event_id=uuid5(
                    NAMESPACE_URL,
                    f"{previous.gap_id}:RESOLVED:{reason.strip()}",
                ),
                gap_id=previous.gap_id,
                signal_id=signal_id,
                session_date=session_date,
                calendar_version=calendar_version.strip(),
                status="RESOLVED",
                reason=reason.strip(),
                recorded_at=resolved_at,
            )
            transaction.record_session_gap_event(resolved)
            return resolved

        return self._execute_in_transaction(persist, transaction)

    def session_gap_events(
        self, signal_id: UUID
    ) -> tuple[LifecycleSessionGapEvent, ...]:
        return self._unit_of_work.execute(
            lambda transaction: transaction.session_gap_events(signal_id)
        )

    def record_daily_bar_correction(
        self,
        signal_id: UUID,
        *,
        original_identity: tuple[str, str, str, datetime, str],
        corrected_bar: CompletedDailyBarObservation,
        operator_id: str,
        reason: str,
        calendar_version: str,
        recorded_at: datetime,
        provider_evidence: ProviderDailyBarEvidence | None = None,
    ) -> LifecycleCorrectionRecord:
        if not operator_id.strip():
            raise ValueError("operator_id is required")
        if not reason.strip():
            raise ValueError("correction reason is required")
        if not calendar_version.strip():
            raise ValueError("calendar_version is required")
        if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware")
        if recorded_at < corrected_bar.observed_at:
            raise ValueError("correction cannot be recorded before corrected evidence")
        if provider_evidence is not None and provider_evidence.bar != corrected_bar:
            raise ValueError("provider evidence bar must match the corrected lifecycle bar")
        if provider_evidence is not None and recorded_at < provider_evidence.retrieved_at:
            raise ValueError("correction cannot be recorded before provider evidence retrieval")
        if original_identity[3].tzinfo is None or original_identity[3].utcoffset() is None:
            raise ValueError("original candle timestamp must be timezone-aware")
        normalized_original = (
            original_identity[0].strip().casefold(),
            original_identity[1].strip().upper(),
            original_identity[2].strip().upper(),
            original_identity[3].astimezone(timezone.utc),
            original_identity[4].strip(),
        )
        corrected_identity = corrected_bar.identity
        if corrected_identity[:4] != normalized_original[:4]:
            raise ValueError("correction must refer to the same provider, symbol, timeframe, and candle")
        if corrected_identity[4] == normalized_original[4]:
            raise ValueError("correction must carry a new source revision")

        correction_id = uuid5(
            NAMESPACE_URL,
            (
                f"signal-correction:{signal_id}:{normalized_original!r}:"
                f"{corrected_identity!r}:{operator_id.strip()}:{reason.strip()}"
            ),
        )
        record = LifecycleCorrectionRecord(
            correction_id=correction_id,
            signal_id=signal_id,
            original_identity=normalized_original,
            corrected_bar=corrected_bar,
            operator_id=operator_id.strip(),
            reason=reason.strip(),
            calendar_version=calendar_version.strip(),
            recorded_at=recorded_at,
            provider_evidence=provider_evidence,
        )

        def persist(transaction: SignalLifecycleTransaction) -> LifecycleCorrectionRecord:
            if transaction.latest_for_signal(signal_id) is None:
                raise ValueError("opportunity identity does not exist")
            if transaction.get_observation(signal_id, normalized_original) is None:
                raise ValueError("correction references a missing original observation")
            transaction.record_correction(record)
            return record

        return self._unit_of_work.execute(persist)

    def lifecycle_corrections(
        self, signal_id: UUID
    ) -> tuple[LifecycleCorrectionRecord, ...]:
        return self._unit_of_work.execute(
            lambda transaction: transaction.corrections(signal_id)
        )

    def record_daily_bar_correction_review(
        self,
        signal_id: UUID,
        correction_id: UUID,
        *,
        decision: str,
        reviewer_id: str,
        reason: str,
        recorded_at: datetime,
    ) -> LifecycleCorrectionReviewDecision:
        allowed_decisions = {
            "REJECTED",
            "ACCEPTED_NO_STATE_CHANGE",
            "REPLAY_REQUIRED",
        }
        normalized_decision = decision.strip().upper()
        if normalized_decision not in allowed_decisions:
            raise ValueError("unsupported lifecycle correction review decision")
        if not reviewer_id.strip() or not reason.strip():
            raise ValueError("reviewer_id and review reason are required")
        if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware")

        decision_id = uuid5(
            NAMESPACE_URL,
            (
                f"signal-correction-review:{signal_id}:{correction_id}:"
                f"{normalized_decision}:{reviewer_id.strip()}:{reason.strip()}"
            ),
        )
        review = LifecycleCorrectionReviewDecision(
            decision_id=decision_id,
            correction_id=correction_id,
            signal_id=signal_id,
            decision=normalized_decision,
            reviewer_id=reviewer_id.strip(),
            reason=reason.strip(),
            recorded_at=recorded_at,
        )

        def persist(transaction: SignalLifecycleTransaction) -> LifecycleCorrectionReviewDecision:
            correction = next(
                (
                    item for item in transaction.corrections(signal_id)
                    if item.correction_id == correction_id
                ),
                None,
            )
            if correction is None:
                raise ValueError("correction identity does not exist")
            if correction.operator_id == reviewer_id.strip():
                raise ValueError("correction author cannot review their own correction")
            if recorded_at < correction.recorded_at:
                raise ValueError("review cannot precede correction intake")
            prior_reviews = [
                item
                for item in transaction.correction_review_decisions(signal_id)
                if item.correction_id == correction_id
            ]
            if prior_reviews and recorded_at < prior_reviews[-1].recorded_at:
                raise ValueError("correction review decisions must be chronological")
            transaction.record_correction_review_decision(review)
            return review

        return self._unit_of_work.execute(persist)

    def rebuild_daily_bar_correction(
        self,
        signal_id: UUID,
        correction_id: UUID,
        *,
        operator_id: str,
        recorded_at: datetime,
    ) -> LifecycleCorrectionRebuildRecord:
        if not operator_id.strip():
            raise ValueError("operator_id is required")
        if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware")

        def persist(transaction: SignalLifecycleTransaction) -> LifecycleCorrectionRebuildRecord:
            corrections = transaction.corrections(signal_id)
            correction = next((candidate for candidate in corrections if candidate.correction_id == correction_id), None)
            if correction is None:
                raise ValueError("correction identity does not exist")
            rebuilds = transaction.correction_rebuilds(signal_id)
            existing = next((candidate for candidate in rebuilds if candidate.correction_id == correction_id), None)
            if existing is not None:
                return existing

            reviews = [review_item for review_item in transaction.correction_review_decisions(signal_id) if review_item.correction_id == correction_id]
            if not reviews or reviews[-1].decision != "REPLAY_REQUIRED":
                raise ValueError("correction must have a latest REPLAY_REQUIRED review before replay")
            completed_ids = {rebuild_item.correction_id for rebuild_item in rebuilds}
            latest_review_by_id: dict[UUID, LifecycleCorrectionReviewDecision] = {}
            for review_item in transaction.correction_review_decisions(signal_id):
                latest_review_by_id[review_item.correction_id] = review_item
            for correction_item in corrections:
                if correction_item.correction_id == correction_id:
                    continue
                decision = latest_review_by_id.get(correction_item.correction_id)
                if decision is None or (decision.decision == "REPLAY_REQUIRED" and correction_item.correction_id not in completed_ids):
                    raise ValueError("another unresolved correction blocks chronological replay")

            history = transaction.signal_history(signal_id)
            publication = next((history_item for history_item in history if history_item.event in {"PUBLISHED", "PUBLISHED_VERSION"}), None)
            if publication is None:
                raise ValueError("published opportunity baseline is missing")
            latest = transaction.latest_for_signal(signal_id)
            if latest is None:
                raise ValueError("opportunity identity does not exist")
            if latest.event in {"STATUS_EXPIRED", "STATUS_CLOSED", "EVIDENCE_CHANGED_INVALIDATED"}:
                raise ValueError("correction replay cannot rewrite an independent terminal lifecycle decision")
            if latest.signal.status not in {SignalStatus.ACTIVE, SignalStatus.TRIGGERED, SignalStatus.INVALIDATED}:
                raise ValueError("opportunity status is not eligible for correction replay")
            if recorded_at < latest.recorded_at:
                raise ValueError("rebuild timestamp cannot precede the current lifecycle history")

            observations = transaction.observations(signal_id)
            original_observation = next(
                (observation_item for observation_item in observations if observation_item.bar.identity == correction.original_identity),
                None,
            )
            if original_observation is None:
                raise ValueError("original observation for correction is missing")
            replaced_originals = {
                correction_item.original_identity for correction_item in corrections
                if correction_item.correction_id in completed_ids or correction_item.correction_id == correction_id
            }
            effective = [observation_item for observation_item in observations if observation_item.bar.identity not in replaced_originals]
            effective.append(LifecycleObservationRecord(
                signal_id=signal_id,
                bar=correction.corrected_bar,
                policy_version=original_observation.policy_version,
                calendar_version=correction.calendar_version,
                resulting_status=SignalStatus.ACTIVE,
                provider_evidence=correction.provider_evidence,
            ))
            by_session: dict[datetime, LifecycleObservationRecord] = {}
            for observation_item in sorted(effective, key=lambda value: (value.bar.candle_at, value.bar.observed_at, value.bar.revision)):
                previous_observation = by_session.get(observation_item.bar.candle_at)
                if previous_observation is not None and previous_observation.bar.provider.strip().casefold() != observation_item.bar.provider.strip().casefold():
                    raise ValueError("multiple providers exist for one replayed session; explicit source reconciliation is required")
                if previous_observation is None or observation_item.bar.observed_at > previous_observation.bar.observed_at:
                    by_session[observation_item.bar.candle_at] = observation_item
            ordered = tuple(by_session[key] for key in sorted(by_session))
            if not ordered:
                raise ValueError("no completed daily observations are available for replay")

            rebuilt = publication.signal
            trace: list[dict[str, object]] = []
            corrected_status: SignalStatus | None = None
            for ordered_observation in ordered:
                rebuilt = transition_signal_from_completed_daily_bar(rebuilt, ordered_observation.bar)
                trace.append({
                    "provider": ordered_observation.bar.identity[0],
                    "symbol": ordered_observation.bar.identity[1],
                    "timeframe": ordered_observation.bar.identity[2],
                    "candle_at": ordered_observation.bar.candle_at.isoformat(),
                    "revision": ordered_observation.bar.revision,
                    "source_reference": ordered_observation.bar.source_reference,
                    "finality_attestation": ordered_observation.bar.finality_attestation,
                    "open": str(ordered_observation.bar.open),
                    "high": str(ordered_observation.bar.high),
                    "low": str(ordered_observation.bar.low),
                    "close": str(ordered_observation.bar.close),
                    "policy_version": ordered_observation.policy_version,
                    "calendar_version": ordered_observation.calendar_version,
                    "resulting_status": rebuilt.status.value,
                    "provider_evidence": (
                        {
                            "provider_id": ordered_observation.provider_evidence.provider_id,
                            "provider_contract_version": ordered_observation.provider_evidence.provider_contract_version,
                            "instrument_symbol": ordered_observation.provider_evidence.instrument_symbol,
                            "session_date": ordered_observation.provider_evidence.session_date.isoformat(),
                            "source_timestamp": ordered_observation.provider_evidence.source_timestamp.isoformat(),
                            "retrieved_at": ordered_observation.provider_evidence.retrieved_at.isoformat(),
                        }
                        if ordered_observation.provider_evidence is not None
                        else None
                    ),
                })
                if ordered_observation.bar.identity == correction.corrected_bar.identity:
                    corrected_status = rebuilt.status
            if corrected_status is None:
                raise ValueError("corrected candle was not included in chronological replay")

            transaction.record_observation(LifecycleObservationRecord(
                signal_id=signal_id,
                bar=correction.corrected_bar,
                policy_version=original_observation.policy_version,
                calendar_version=correction.calendar_version,
                resulting_status=corrected_status,
                provider_evidence=correction.provider_evidence,
            ))
            previous_status = latest.signal.status
            superseded_event_id: UUID | None = None
            correction_event_id: UUID | None = None

            if rebuilt.status is not previous_status:
                prior_terminal = next((item for item in reversed(history) if item.event in {"STATUS_TRIGGERED", "STATUS_INVALIDATED"}), None)
                reference_event_id: UUID | None = None
                if prior_terminal is not None:
                    prior_observation = next((
                        item for item in observations
                        if item.bar.observed_at == prior_terminal.recorded_at
                        and item.resulting_status is prior_terminal.signal.status
                    ), None)
                    if prior_observation is not None:
                        reference_event_id = uuid5(
                            NAMESPACE_URL,
                            f"signal-daily-bar:{signal_id}:{prior_observation.bar.identity!r}:{prior_observation.policy_version}:{prior_observation.calendar_version}",
                        )
                else:
                    reference_event_id = uuid5(
                        NAMESPACE_URL,
                        f"signal-published:{signal_id}:{snapshot_signal(publication.signal)!r}",
                    )

                if reference_event_id is not None:
                    if transaction.supersede_alert(reference_event_id, f"superseded by correction replay {correction_id}", now=recorded_at):
                        superseded_event_id = reference_event_id
                    recipients = transaction.delivered_recipients(reference_event_id)
                    if recipients:
                        correction_event_id = uuid5(
                            NAMESPACE_URL,
                            f"signal-correction:{signal_id}:{correction_id}:{reference_event_id}:{previous_status.value}:{rebuilt.status.value}",
                        )
                        transaction.publish_alert(AlertEvent(
                            event_id=correction_event_id,
                            signal_id=signal_id,
                            symbol=rebuilt.symbol,
                            event_type=AlertEventType.SIGNAL_CORRECTED,
                            occurred_at=recorded_at,
                            message=(
                                f"{rebuilt.symbol} lifecycle correction: previously communicated "
                                f"{previous_status.value}; chronological rebuild now reports "
                                f"{rebuilt.status.value}. The earlier event remains in the audit history."
                            ),
                            signal_snapshot=snapshot_signal(rebuilt),
                            recipient_user_ids=recipients,
                            correction_of_event_id=reference_event_id,
                        ))
                transaction.record_signal(
                    rebuilt,
                    f"CORRECTION_REPLAY_REBUILT:{correction_id}",
                    recorded_at,
                    signal_id=signal_id,
                )

            digest_payload = json.dumps({
                "signal_id": str(signal_id),
                "correction_id": str(correction_id),
                "policy_versions": sorted({item.policy_version for item in ordered}),
                "calendar_versions": sorted({item.calendar_version for item in ordered}),
                "trace": trace,
            }, sort_keys=True, separators=(",", ":"))
            result = LifecycleCorrectionRebuildRecord(
                rebuild_id=uuid5(NAMESPACE_URL, f"signal-correction-rebuild:{correction_id}"),
                correction_id=correction_id,
                signal_id=signal_id,
                operator_id=operator_id.strip(),
                previous_status=previous_status,
                resulting_status=rebuilt.status,
                observation_count=len(ordered),
                replay_digest=hashlib.sha256(digest_payload.encode("utf-8")).hexdigest(),
                superseded_event_id=superseded_event_id,
                correction_event_id=correction_event_id,
                recorded_at=recorded_at,
            )
            transaction.record_correction_rebuild(result)
            return result

        return self._unit_of_work.execute(persist)

    def lifecycle_correction_review_decisions(
        self, signal_id: UUID
    ) -> tuple[LifecycleCorrectionReviewDecision, ...]:
        return self._unit_of_work.execute(
            lambda transaction: transaction.correction_review_decisions(signal_id)
        )

    def lifecycle_correction_rebuilds(
        self, signal_id: UUID
    ) -> tuple[LifecycleCorrectionRebuildRecord, ...]:
        return self._unit_of_work.execute(
            lambda transaction: transaction.correction_rebuilds(signal_id)
        )

    def latest_completed_observation(
        self,
        signal_id: UUID,
        *,
        transaction: SignalLifecycleTransaction | None = None,
    ) -> LifecycleObservationRecord | None:
        return self._execute_in_transaction(
            lambda current: current.latest_observation(signal_id), transaction
        )

    def expire_opportunity(
        self,
        signal_id: UUID,
        *,
        eligible_sessions: tuple[date, ...],
        calendar_version: str,
        evaluated_at: datetime,
        transaction: SignalLifecycleTransaction | None = None,
    ) -> SignalLifecycleResult | None:
        if len(eligible_sessions) < 20:
            raise ValueError("opportunity expiry requires 20 eligible sessions")
        if any(
            later <= earlier
            for earlier, later in zip(eligible_sessions, eligible_sessions[1:])
        ):
            raise ValueError("eligible sessions must be strictly chronological")
        if not calendar_version or not calendar_version.strip():
            raise ValueError("calendar_version is required")
        if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
            raise ValueError("evaluated_at must be timezone-aware")

        def persist(transaction: SignalLifecycleTransaction) -> SignalLifecycleResult | None:
            latest = transaction.latest_for_signal(signal_id)
            if latest is None or latest.signal.status is not SignalStatus.ACTIVE:
                return None
            if latest.event not in {"PUBLISHED", "PUBLISHED_VERSION"}:
                return None

            expired = replace(latest.signal, status=SignalStatus.EXPIRED)
            final_session = eligible_sessions[-1]
            event_id = uuid5(
                NAMESPACE_URL,
                f"signal-expired:{signal_id}:{final_session.isoformat()}:{calendar_version.strip()}",
            )
            transaction.record_signal(
                expired,
                "STATUS_EXPIRED",
                evaluated_at,
                signal_id=signal_id,
            )
            transaction.publish_alert(
                AlertEvent(
                    event_id=event_id,
                    signal_id=signal_id,
                    symbol=expired.symbol,
                    event_type=AlertEventType.SIGNAL_EXPIRED,
                    occurred_at=evaluated_at,
                    message=(
                        f"{expired.symbol} opportunity expired after "
                        f"{len(eligible_sessions)} eligible EGX sessions "
                        f"through {final_session.isoformat()} "
                        f"(calendar {calendar_version.strip()})"
                    ),
                    signal_snapshot=snapshot_signal(expired),
                )
            )
            return SignalLifecycleResult(
                signal_id=signal_id,
                signal=expired,
                changed=True,
                outcome_recorded=False,
                alert_published=True,
            )

        return self._execute_in_transaction(persist, transaction)

    def invalidate_for_evidence_change(
        self,
        candidate: Signal | None,
        *,
        observed_at: datetime,
    ) -> SignalLifecycleResult | None:
        """Invalidate an active setup when supporting evidence changes.

        A missing candidate is not treated as contradictory evidence. Evidence
        invalidation is not a market-proxy outcome because no market exit was observed.
        """
        if candidate is None:
            return None
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")

        def persist(transaction: SignalLifecycleTransaction) -> SignalLifecycleResult | None:
            latest = transaction.latest_for_identity(
                candidate.symbol,
                candidate.strategy_id,
                candidate.strategy_version,
                candidate.generated_at,
            )
            if latest is None or latest.signal.status is not SignalStatus.ACTIVE:
                return None

            current = latest.signal
            if not self._supporting_evidence_changed(current, candidate):
                return SignalLifecycleResult(
                    signal_id=latest.signal_id,
                    signal=current,
                    changed=False,
                    outcome_recorded=False,
                    alert_published=False,
                )

            invalidated = replace(current, status=SignalStatus.INVALIDATED)
            event_id = uuid5(
                NAMESPACE_URL,
                f"signal-evidence-change:{latest.signal_id}:{candidate!r}",
            )
            event = AlertEvent(
                event_id=event_id,
                signal_id=latest.signal_id,
                symbol=current.symbol,
                event_type=AlertEventType.SIGNAL_INVALIDATED,
                occurred_at=observed_at,
                message=(
                    f"{current.symbol} signal invalidated because its supporting "
                    "analysis evidence changed"
                ),
                signal_snapshot=snapshot_signal(invalidated),
            )
            transaction.record_signal(
                invalidated,
                "EVIDENCE_CHANGED_INVALIDATED",
                observed_at,
                signal_id=latest.signal_id,
            )
            transaction.publish_alert(event)
            return SignalLifecycleResult(
                signal_id=latest.signal_id,
                signal=invalidated,
                changed=True,
                outcome_recorded=False,
                alert_published=True,
            )

        return self._unit_of_work.execute(persist)

    @staticmethod
    def _supporting_evidence_changed(previous: Signal, candidate: Signal) -> bool:
        return any(
            (
                previous.symbol.strip().upper() != candidate.symbol.strip().upper(),
                previous.direction != candidate.direction,
                previous.timeframe != candidate.timeframe,
                previous.entry_zone != candidate.entry_zone,
                previous.invalidation != candidate.invalidation,
                previous.targets != candidate.targets,
                previous.confidence != candidate.confidence,
                previous.risk_score != candidate.risk_score,
                previous.evidence != candidate.evidence,
                previous.strategy_id != candidate.strategy_id,
                previous.strategy_version != candidate.strategy_version,
            )
        )

    @staticmethod
    def _build_alert(
        signal_id: UUID,
        signal: Signal,
        occurred_at: datetime,
    ) -> AlertEvent:
        event_type = (
            AlertEventType.SIGNAL_TRIGGERED
            if signal.status is SignalStatus.TRIGGERED
            else AlertEventType.SIGNAL_INVALIDATED
        )
        event_id = uuid5(
            NAMESPACE_URL,
            f"signal-lifecycle:{signal_id}:{event_type.value}:{occurred_at.isoformat()}",
        )
        return AlertEvent(
            event_id=event_id,
            signal_id=signal_id,
            symbol=signal.symbol,
            event_type=event_type,
            occurred_at=occurred_at,
            message=f"{signal.symbol} signal {event_type.value.lower().replace('_', ' ')}",
            signal_snapshot=snapshot_signal(signal),
        )

    @staticmethod
    def _build_outcome(
        signal_id: UUID,
        signal: Signal,
        state: SignalMarketState,
        entry_price: Decimal,
    ) -> SignalOutcomeRecord:
        if signal.status is SignalStatus.TRIGGERED:
            target = (
                min(signal.targets, key=lambda item: item.price)
                if signal.direction is SignalDirection.BUY
                else max(signal.targets, key=lambda item: item.price)
            )
            outcome = SignalOutcome.TARGET_HIT
            exit_price = state.price
            target_label = target.label
        else:
            outcome = SignalOutcome.INVALIDATED
            exit_price = signal.invalidation
            target_label = None

        if signal.direction is SignalDirection.BUY:
            price_move = exit_price - entry_price
            risk = entry_price - signal.invalidation
        else:
            price_move = entry_price - exit_price
            risk = signal.invalidation - entry_price

        if risk <= 0:
            raise ValueError("entry price must leave positive risk to invalidation")

        return SignalOutcomeRecord(
            signal_id=signal_id,
            symbol=signal.symbol,
            outcome=outcome,
            direction=signal.direction,
            observed_at=state.observed_at,
            entry_price=entry_price,
            exit_price=exit_price,
            realized_return=price_move / entry_price,
            realized_r=price_move / risk,
            invalidation=signal.invalidation,
            target_label=target_label,
            strategy_id=signal.strategy_id,
            strategy_version=signal.strategy_version,
            data_timestamp=state.data_timestamp,
        )
