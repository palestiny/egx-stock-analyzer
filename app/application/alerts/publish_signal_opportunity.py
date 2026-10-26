from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from app.application.alerts.outbox import AlertOutbox
from app.application.alerts.signal_snapshot import snapshot_signal
from app.application.signals.store import SignalHistoryStore, SignalRecord
from app.domain.alerts.model import AlertEvent, AlertEventType
from app.domain.signals.model import Signal, SignalStatus


@dataclass(frozen=True)
class SignalPublicationResult:
    signal_id: UUID
    event_id: UUID
    signal_record: SignalRecord
    queued_new_event: bool


class PublishSignalOpportunity:
    """Persist and enqueue a new active signal as an immutable opportunity event."""

    def __init__(
        self,
        *,
        history: SignalHistoryStore,
        outbox: AlertOutbox,
    ) -> None:
        self._history = history
        self._outbox = outbox

    def execute(
        self,
        signal: Signal,
        *,
        recorded_at: datetime,
    ) -> SignalPublicationResult | None:
        if signal.status is not SignalStatus.ACTIVE:
            raise ValueError("only active signals can be published as new opportunities")
        if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware")

        snapshot = snapshot_signal(signal)
        latest = self._history.latest(signal.symbol)
        same_identity = (
            latest is not None
            and latest.signal.strategy_id == signal.strategy_id
            and latest.signal.strategy_version == signal.strategy_version
            and latest.signal.generated_at == signal.generated_at
        )

        if same_identity and latest is not None:
            signal_id = latest.signal_id
            if latest.signal.status is not SignalStatus.ACTIVE:
                return None
            history_records = self._history.history(signal_id)
            already_recorded = any(
                item.event in {"PUBLISHED", "PUBLISHED_VERSION"}
                and item.signal == signal
                for item in history_records
            )
            if latest.signal != signal:
                signal_record = self._history.record(
                    signal,
                    "PUBLISHED_VERSION",
                    recorded_at,
                )
            elif already_recorded:
                signal_record = latest
            else:
                signal_record = self._history.record(
                    signal,
                    "PUBLISHED",
                    recorded_at,
                )
        else:
            signal_record = self._history.record(
                signal,
                "PUBLISHED",
                recorded_at,
            )
            signal_id = signal_record.signal_id

        event_id = uuid5(
            NAMESPACE_URL,
            f"signal-published:{signal_id}:{snapshot!r}",
        )
        existing_event = self._outbox.get(event_id)
        self._outbox.publish(
            AlertEvent(
                event_id=event_id,
                signal_id=signal_id,
                symbol=signal.symbol,
                event_type=AlertEventType.SIGNAL_PUBLISHED,
                occurred_at=signal.generated_at,
                message=(
                    f"{signal.symbol} opportunity published from "
                    f"{signal.strategy_id} v{signal.strategy_version}"
                ),
                signal_snapshot=snapshot,
            )
        )
        return SignalPublicationResult(
            signal_id=signal_id,
            event_id=event_id,
            signal_record=signal_record,
            queued_new_event=existing_event is None,
        )
