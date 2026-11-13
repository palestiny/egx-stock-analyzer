from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from app.application.alerts.in_memory import InMemoryAlertPublisher
from app.application.alerts.ports import AlertPublisher
from app.application.alerts.signal_snapshot import snapshot_signal
from app.application.signals.lifecycle_unit_of_work import (
    LifecycleCorrectionRecord,
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

    def process_completed_daily_bar(
        self,
        signal_id: UUID,
        bar: CompletedDailyBarObservation,
        *,
        calendar_version: str,
        policy_version: str = "dec138-daily-ohlc-v1",
        resolved_gap_session_date: date | None = None,
        resolved_gap_at: datetime | None = None,
    ) -> SignalLifecycleResult | None:
        """Evaluate one provider-attested completed candle for a published signal.

        This path records market-level evidence only. It never invents an entry
        fill or creates realized return/R accounting.
        """
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
            }:
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

        return self._unit_of_work.execute(persist)

    def mark_session_gap(
        self,
        signal_id: UUID,
        *,
        session_date: date,
        calendar_version: str,
        reason: str,
        detected_at: datetime,
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

        return self._unit_of_work.execute(persist)

    def resolve_session_gap(
        self,
        signal_id: UUID,
        *,
        session_date: date,
        calendar_version: str,
        reason: str,
        resolved_at: datetime,
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

        return self._unit_of_work.execute(persist)

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

    def latest_completed_observation(
        self, signal_id: UUID
    ) -> LifecycleObservationRecord | None:
        return self._unit_of_work.execute(
            lambda transaction: transaction.latest_observation(signal_id)
        )

    def expire_opportunity(
        self,
        signal_id: UUID,
        *,
        eligible_sessions: tuple[date, ...],
        calendar_version: str,
        evaluated_at: datetime,
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

        return self._unit_of_work.execute(persist)

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
