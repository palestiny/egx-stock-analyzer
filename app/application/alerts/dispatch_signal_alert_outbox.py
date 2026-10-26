from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.application.alerts.outbox import AlertOutbox, AlertOutboxRecord
from app.application.alerts.telegram_delivery_store import (
    SignalAlertDeliveryStatus,
    SignalAlertDeliveryStore,
)
from app.application.notifications.telegram_account_linking import (
    LinkedTelegramAccount,
)
from app.application.notifications.telegram_message_sender import TelegramMessageSender
from app.application.signals.store import SignalHistoryStore
from app.application.subscriptions.entitlement_evaluator import EntitlementDecision
from app.domain.signals.model import Signal


class EntitlementAccessEvaluator(Protocol):
    def evaluate(
        self,
        user_id: UUID,
        entitlement_code: str,
        *,
        now: datetime,
    ) -> EntitlementDecision: ...


class TelegramRecipientDirectory(Protocol):
    def list_linked_accounts(self) -> tuple[LinkedTelegramAccount, ...]: ...


@dataclass(frozen=True)
class DispatchBatchResult:
    events_processed: int
    recipients_delivered: int
    recipients_suppressed: int
    recipients_failed: int


class DispatchSignalAlertOutbox:
    """Deliver persisted signal events to linked Telegram users with entitlements."""

    CHANNEL = "telegram"
    ENTITLEMENT = "telegram_opportunities"

    def __init__(
        self,
        *,
        outbox: AlertOutbox,
        recipients: TelegramRecipientDirectory,
        deliveries: SignalAlertDeliveryStore,
        history: SignalHistoryStore,
        entitlements: EntitlementAccessEvaluator,
        transport: TelegramMessageSender,
    ) -> None:
        self._outbox = outbox
        self._recipients = recipients
        self._deliveries = deliveries
        self._history = history
        self._entitlements = entitlements
        self._transport = transport

    def execute(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> DispatchBatchResult:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        if limit < 1:
            raise ValueError("limit must be positive")

        events = self._outbox.pending(limit)
        recipients = self._recipients.list_linked_accounts()
        delivered = 0
        suppressed = 0
        failed = 0

        for record in events:
            event_failed = False
            signal_record = self._history.get(record.event.signal_id)
            for recipient in recipients:
                existing = self._deliveries.get(
                    record.event.event_id,
                    recipient.user_id,
                    self.CHANNEL,
                )
                if existing is not None and existing.status in {
                    SignalAlertDeliveryStatus.DELIVERED,
                    SignalAlertDeliveryStatus.SUPPRESSED,
                }:
                    continue

                if existing is None:
                    self._deliveries.create_pending(
                        record.event.event_id,
                        recipient.user_id,
                        self.CHANNEL,
                        now=now,
                    )
                decision = self._entitlements.evaluate(
                    recipient.user_id,
                    self.ENTITLEMENT,
                    now=now,
                )
                if not decision.allowed:
                    self._deliveries.mark_suppressed(
                        record.event.event_id,
                        recipient.user_id,
                        self.CHANNEL,
                        decision.reason,
                        now=now,
                    )
                    suppressed += 1
                    continue

                if signal_record is None:
                    self._deliveries.mark_failed(
                        record.event.event_id,
                        recipient.user_id,
                        self.CHANNEL,
                        "signal history unavailable",
                        now=now,
                    )
                    failed += 1
                    event_failed = True
                    continue

                message = self._format_message(record, signal_record.signal)
                try:
                    self._transport.send_message(recipient.chat_id, message)
                except Exception as error:
                    # Transport exception strings can contain sensitive request details.
                    self._deliveries.mark_failed(
                        record.event.event_id,
                        recipient.user_id,
                        self.CHANNEL,
                        f"transport error: {error.__class__.__name__}",
                        now=now,
                    )
                    failed += 1
                    event_failed = True
                    continue

                self._deliveries.mark_delivered(
                    record.event.event_id,
                    recipient.user_id,
                    self.CHANNEL,
                    now=now,
                )
                delivered += 1

            if event_failed:
                self._outbox.mark_failed(
                    record.event.event_id,
                    "one or more recipient deliveries failed",
                )
            else:
                self._outbox.mark_delivered(record.event.event_id, now)

        return DispatchBatchResult(
            events_processed=len(events),
            recipients_delivered=delivered,
            recipients_suppressed=suppressed,
            recipients_failed=failed,
        )

    @staticmethod
    def _format_message(record: AlertOutboxRecord, signal: Signal) -> str:
        targets = "\n".join(
            f"- {target.label}: {target.price}" for target in signal.targets
        )
        evidence = "\n".join(
            f"- {item.kind}: {item.description}" for item in signal.evidence
        )
        return (
            "EGX Stock Analyzer — Opportunity Update\n"
            f"Symbol: {signal.symbol}\n"
            f"Event: {record.event.event_type.value}\n"
            f"Direction: {signal.direction.value}\n"
            f"Status: {signal.status.value}\n"
            f"Timeframe: {signal.timeframe}\n"
            f"Entry zone: {signal.entry_zone.lower} – {signal.entry_zone.upper}\n"
            f"Invalidation: {signal.invalidation}\n"
            f"Targets:\n{targets}\n"
            f"Evidence:\n{evidence}\n"
            f"Strategy: {signal.strategy_id} v{signal.strategy_version}\n"
            f"Generated: {signal.generated_at.isoformat()}\n"
            f"Data timestamp: {signal.data_timestamp.isoformat()}\n"
            f"Update: {record.event.message}\n"
            f"Event reference: {record.event.event_id}\n"
            "Market-price observation is not proof of an executed trade. "
            "Analysis is uncertain and is not a guarantee of returns."
        )
