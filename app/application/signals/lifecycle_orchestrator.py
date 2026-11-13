from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from app.application.alerts.in_memory import InMemoryAlertPublisher
from app.application.alerts.ports import AlertPublisher
from app.application.alerts.signal_snapshot import snapshot_signal
from app.application.signals.lifecycle_unit_of_work import (
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
            latest = transaction.latest(signal.symbol)
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
        bar: CompletedDailyBarObservation,
        *,
        calendar_version: str,
        policy_version: str = "dec138-daily-ohlc-v1",
    ) -> SignalLifecycleResult | None:
        """Evaluate one provider-attested completed candle for a published signal.

        This path records market-level evidence only. It never invents an entry
        fill or creates realized return/R accounting.
        """
        if not policy_version or not policy_version.strip():
            raise ValueError("policy_version is required")
        if not calendar_version or not calendar_version.strip():
            raise ValueError("calendar_version is required")

        def persist(transaction: SignalLifecycleTransaction) -> SignalLifecycleResult | None:
            latest = transaction.latest(bar.symbol)
            if latest is None:
                return None
            if latest.event not in {"PUBLISHED", "PUBLISHED_VERSION"}:
                return None
            if latest.signal.status is not SignalStatus.ACTIVE:
                return SignalLifecycleResult(
                    signal_id=latest.signal_id,
                    signal=latest.signal,
                    changed=False,
                    outcome_recorded=False,
                    alert_published=False,
                )

            existing = transaction.get_observation(bar.identity)
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
                if not same_source_payload or existing.signal_id != latest.signal_id:
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
            latest = transaction.latest(candidate.symbol)
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
                invalidated, "EVIDENCE_CHANGED_INVALIDATED", observed_at
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
