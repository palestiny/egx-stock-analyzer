from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from app.application.alerts.ports import AlertPublisher
from app.application.signals.store import SignalHistoryStore
from app.application.signals.track_record import TrackRecordStore
from app.domain.alerts.model import AlertEvent, AlertEventType
from app.domain.signals.lifecycle import SignalMarketState, transition_signal
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
    """Coordinate one deterministic lifecycle observation and its side effects.

    The domain transition remains pure. This application boundary is responsible
    for stable signal identity, lifecycle history, alerts, and terminal outcomes.
    Side effects use deterministic IDs/idempotent stores so retries do not duplicate
    an alert or terminal outcome.
    """

    def __init__(
        self,
        history: SignalHistoryStore,
        alerts: AlertPublisher,
        track_record: TrackRecordStore,
    ) -> None:
        self._history = history
        self._alerts = alerts
        self._track_record = track_record

    def process(
        self,
        signal: Signal,
        state: SignalMarketState,
        *,
        entry_price: Decimal,
    ) -> SignalLifecycleResult:
        if entry_price <= 0:
            raise ValueError("entry price must be positive")

        latest = self._history.latest(signal.symbol)
        if (
            latest is not None
            and latest.signal.strategy_id == signal.strategy_id
            and latest.signal.strategy_version == signal.strategy_version
            and latest.signal.generated_at == signal.generated_at
        ):
            signal_id = latest.signal_id
            current = latest.signal
        else:
            created = self._history.record(signal, "CREATED", signal.generated_at)
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

        alert_event = self._build_alert(signal_id, transitioned, state.observed_at)
        self._alerts.publish(alert_event)

        outcome_recorded = False
        if transitioned.status in (SignalStatus.TRIGGERED, SignalStatus.INVALIDATED):
            outcome = self._build_outcome(
                signal_id, transitioned, state, entry_price
            )
            self._track_record.record(outcome)
            outcome_recorded = True

        self._history.record(
            transitioned,
            f"STATUS_{transitioned.status.value}",
            state.observed_at,
        )
        return SignalLifecycleResult(
            signal_id=signal_id,
            signal=transitioned,
            changed=True,
            outcome_recorded=outcome_recorded,
            alert_published=True,
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
            data_timestamp=signal.data_timestamp,
        )
