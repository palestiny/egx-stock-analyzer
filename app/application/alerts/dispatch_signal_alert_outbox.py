from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from app.application.alerts.outbox import AlertOutbox, AlertOutboxRecord
from app.application.alerts.signal_snapshot import snapshot_signal
from app.application.identity.user_store import UserStore
from app.application.alerts.telegram_delivery_store import (
    SignalAlertDeliveryStatus,
    SignalAlertDeliveryStore,
)
from app.application.notifications.telegram_account_linking import (
    LinkedTelegramAccount,
)
from app.application.notifications.telegram_message_sender import (
    TelegramDeliveryRejected,
    TelegramMessageSender,
)
from app.application.signals.store import SignalHistoryStore
from app.application.subscriptions.entitlement_evaluator import EntitlementDecision
from app.domain.alerts.model import AlertSignalSnapshot


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
    events_suppressed_no_recipients: int = 0
    events_suppressed_no_eligible_recipients: int = 0


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
        users: UserStore,
        history: SignalHistoryStore,
        entitlements: EntitlementAccessEvaluator,
        transport: TelegramMessageSender,
    ) -> None:
        self._outbox = outbox
        self._recipients = recipients
        self._deliveries = deliveries
        self._users = users
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
        timeout_seconds = self._transport.timeout_seconds
        if timeout_seconds <= 0:
            raise ValueError("Telegram transport timeout must be positive")

        # A process restart may leave pre-send claims or in-flight sends behind.
        # Only pre-send claims are safe to reclaim; an expired send becomes unknown.
        self._deliveries.recover_expired_claims(now=now)
        events = self._outbox.pending(limit)
        recipients = self._recipients.list_linked_accounts()
        delivered = 0
        suppressed = 0
        failed = 0
        suppressed_no_recipients = 0
        suppressed_no_eligible_recipients = 0
        processed_events = 0

        for record in events:
            if not recipients:
                self._outbox.mark_suppressed_no_recipients(
                    record.event.event_id,
                    "no linked Telegram recipients at dispatch time",
                )
                suppressed_no_recipients += 1
                processed_events += 1
                continue

            event_failed = False
            event_had_delivery = False
            event_has_unresolved_delivery = False
            processed_events += 1
            signal_snapshot = record.event.signal_snapshot
            if signal_snapshot is None:
                signal_record = self._history.get(record.event.signal_id)
                if signal_record is not None:
                    signal_snapshot = snapshot_signal(signal_record.signal)

            for recipient in recipients:
                existing = self._deliveries.get(
                    record.event.event_id,
                    recipient.user_id,
                    self.CHANNEL,
                )
                if existing is not None and existing.status is SignalAlertDeliveryStatus.DELIVERED:
                    event_had_delivery = True
                    continue
                if existing is not None and existing.status is SignalAlertDeliveryStatus.SUPPRESSED:
                    continue
                if existing is not None and existing.status in {
                    SignalAlertDeliveryStatus.NOT_DELIVERED,
                    SignalAlertDeliveryStatus.RETRY_EXHAUSTED,
                }:
                    event_failed = True
                    continue
                if existing is not None and existing.status in {
                    SignalAlertDeliveryStatus.CLAIMED,
                    SignalAlertDeliveryStatus.SENDING,
                    SignalAlertDeliveryStatus.DELIVERY_UNKNOWN,
                }:
                    event_has_unresolved_delivery = True
                    continue

                if existing is None:
                    self._deliveries.create_pending(
                        record.event.event_id,
                        recipient.user_id,
                        self.CHANNEL,
                        now=now,
                    )
                user = self._users.get(recipient.user_id)
                if user is None or not user.can_access_protected_resources():
                    suppression = self._deliveries.mark_suppressed(
                        record.event.event_id,
                        recipient.user_id,
                        self.CHANNEL,
                        "user_inactive_or_missing",
                        now=now,
                    )
                    if suppression.status is SignalAlertDeliveryStatus.SUPPRESSED:
                        suppressed += 1
                    elif suppression.status is SignalAlertDeliveryStatus.DELIVERED:
                        event_had_delivery = True
                    else:
                        event_has_unresolved_delivery = True
                    continue

                decision = self._entitlements.evaluate(
                    recipient.user_id,
                    self.ENTITLEMENT,
                    now=now,
                )
                if not decision.allowed:
                    suppression = self._deliveries.mark_suppressed(
                        record.event.event_id,
                        recipient.user_id,
                        self.CHANNEL,
                        decision.reason,
                        now=now,
                    )
                    if suppression.status is SignalAlertDeliveryStatus.SUPPRESSED:
                        suppressed += 1
                    elif suppression.status is SignalAlertDeliveryStatus.DELIVERED:
                        event_had_delivery = True
                    else:
                        event_has_unresolved_delivery = True
                    continue

                if signal_snapshot is None:
                    failure = self._deliveries.mark_failed(
                        record.event.event_id,
                        recipient.user_id,
                        self.CHANNEL,
                        "signal history unavailable",
                        now=now,
                    )
                    if failure.status is SignalAlertDeliveryStatus.FAILED:
                        failed += 1
                        event_failed = True
                    elif failure.status is SignalAlertDeliveryStatus.DELIVERED:
                        event_had_delivery = True
                    else:
                        event_has_unresolved_delivery = True
                    continue

                claim_token = uuid4()
                lease_until = now + timedelta(seconds=timeout_seconds * 2)
                claimed = self._deliveries.claim(
                    record.event.event_id,
                    recipient.user_id,
                    self.CHANNEL,
                    claim_token=claim_token,
                    now=now,
                    lease_until=lease_until,
                )
                if not claimed:
                    event_has_unresolved_delivery = True
                    continue
                if not self._deliveries.mark_sending(
                    record.event.event_id,
                    recipient.user_id,
                    self.CHANNEL,
                    claim_token=claim_token,
                    now=now,
                ):
                    event_has_unresolved_delivery = True
                    continue

                message = self._format_message(record, signal_snapshot)
                try:
                    self._transport.send_message(recipient.chat_id, message)
                except TelegramDeliveryRejected as error:
                    # The provider explicitly rejected the request. This is distinct
                    # from a timeout/connection loss whose remote outcome is unknown.
                    completed = self._deliveries.complete_failed(
                        record.event.event_id,
                        recipient.user_id,
                        self.CHANNEL,
                        f"transport rejected: {error.__class__.__name__}",
                        claim_token=claim_token,
                        now=now,
                    )
                    if completed:
                        failed += 1
                        event_failed = True
                    else:
                        event_has_unresolved_delivery = True
                    continue
                except Exception as error:
                    # Unknown is the safe default for unclassified exceptions after
                    # crossing the network-send boundary; never auto-resend it.
                    self._deliveries.mark_delivery_unknown(
                        record.event.event_id,
                        recipient.user_id,
                        self.CHANNEL,
                        f"transport outcome unknown: {error.__class__.__name__}",
                        claim_token=claim_token,
                        now=now,
                    )
                    event_has_unresolved_delivery = True
                    continue

                completed = self._deliveries.complete_delivered(
                    record.event.event_id,
                    recipient.user_id,
                    self.CHANNEL,
                    claim_token=claim_token,
                    now=now,
                )
                if completed:
                    delivered += 1
                    event_had_delivery = True
                else:
                    # The provider returned success but the worker no longer owns
                    # the lease. Do not overwrite a newer owner's state.
                    event_has_unresolved_delivery = True

            # Another worker or an ambiguous remote outcome may still own/affect a
            # recipient. Do not finalize the event while that work is unresolved.
            if event_has_unresolved_delivery:
                continue
            if event_failed:
                self._outbox.mark_failed(
                    record.event.event_id,
                    "one or more recipient deliveries failed",
                )
            elif event_had_delivery:
                self._outbox.mark_delivered(record.event.event_id, now)
            else:
                self._outbox.mark_suppressed_no_eligible_recipients(
                    record.event.event_id,
                    "no eligible Telegram recipients at dispatch time",
                )
                suppressed_no_eligible_recipients += 1

        return DispatchBatchResult(
            events_processed=processed_events,
            recipients_delivered=delivered,
            recipients_suppressed=suppressed,
            recipients_failed=failed,
            events_suppressed_no_recipients=suppressed_no_recipients,
            events_suppressed_no_eligible_recipients=suppressed_no_eligible_recipients,
        )

    @staticmethod
    def _format_message(
        record: AlertOutboxRecord,
        signal: AlertSignalSnapshot,
    ) -> str:
        targets = "\n".join(
            f"- {target.label}: {target.price}" for target in signal.targets
        )
        evidence = "\n".join(
            f"- {item.kind}: {item.description}" for item in signal.evidence
        )
        message = (
            "EGX Stock Analyzer — Opportunity Update\n"
            f"Symbol: {record.event.symbol}\n"
            f"Event: {record.event.event_type.value}\n"
            f"Direction: {signal.direction}\n"
            f"Status: {signal.status}\n"
            f"Timeframe: {signal.timeframe}\n"
            f"Entry zone: {signal.entry_lower} – {signal.entry_upper}\n"
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
        if len(message) <= 3900:
            return message
        suffix = (
            "\n[Evidence details truncated to fit Telegram's message limit.]"
            f"\nEvent reference: {record.event.event_id}"
            "\nMarket-price observation is not proof of an executed trade. "
            "Analysis is uncertain and is not a guarantee of returns."
        )
        return message[: 3900 - len(suffix)] + suffix
