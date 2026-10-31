from dataclasses import replace
import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.application.alerts.dispatch_signal_alert_outbox import DispatchSignalAlertOutbox
from app.application.alerts.signal_snapshot import snapshot_signal
from app.application.alerts.outbox import AlertOutboxRecord, AlertOutboxStatus
from app.application.alerts.telegram_delivery_store import SignalAlertDeliveryStatus
from app.application.notifications.telegram_account_linking import LinkedTelegramAccount
from app.application.notifications.telegram_message_sender import TelegramDeliveryRejected
from app.application.signals.store import InMemorySignalHistoryStore
from app.application.subscriptions.entitlement_evaluator import EntitlementEvaluator
from app.domain.alerts.model import AlertEvent, AlertEventType
from app.domain.identity.user import User, UserStatus
from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)
from app.domain.subscriptions.model import (
    EntitlementGrant,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from app.infrastructure.notifications.sqlite_alert_outbox import SQLiteAlertOutbox
from app.infrastructure.notifications.sqlite_signal_alert_delivery_store import (
    SQLiteSignalAlertDeliveryStore,
)
from app.infrastructure.persistence.sqlite_subscription_store import SQLiteSubscriptionStore
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore


NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


class FakeRecipients:
    def __init__(self, accounts):
        self._accounts = tuple(accounts)

    def list_linked_accounts(self):
        return self._accounts


class FakeTransport:
    timeout_seconds = 10.0

    def __init__(self, failures: int = 0, ambiguous_failures: int = 0):
        self.failures = failures
        self.ambiguous_failures = ambiguous_failures
        self.sent = []

    def send_message(self, chat_id: str, message: str) -> None:
        if self.ambiguous_failures:
            self.ambiguous_failures -= 1
            raise TimeoutError("sensitive request details must not be persisted")
        if self.failures:
            self.failures -= 1
            raise TelegramDeliveryRejected("provider rejected request")
        self.sent.append((chat_id, message))


def make_signal() -> Signal:
    return Signal(
        symbol="COMI",
        direction=SignalDirection.BUY,
        status=SignalStatus.ACTIVE,
        generated_at=NOW,
        timeframe="1d",
        entry_zone=PriceZone(Decimal("80"), Decimal("81")),
        invalidation=Decimal("78"),
        targets=(Target(Decimal("85"), "T1"), Target(Decimal("88"), "T2")),
        confidence=Decimal("80"),
        risk_score=Decimal("20"),
        evidence=(SignalEvidence("support_rejection", "Rejected support"),),
        strategy_id="price-action",
        strategy_version="1",
        data_timestamp=NOW,
    )


def make_event(signal_id, signal: Signal | None = None) -> AlertEvent:
    return AlertEvent(
        event_id=uuid4(),
        signal_id=signal_id,
        symbol="COMI",
        event_type=AlertEventType.SIGNAL_INVALIDATED,
        occurred_at=NOW,
        message="Supporting evidence changed",
        signal_snapshot=(
            snapshot_signal(replace(signal, status=SignalStatus.INVALIDATED))
            if signal is not None
            else None
        ),
    )


def setup_dispatch(
    tmp_path,
    accounts,
    *,
    failures: int = 0,
    ambiguous_failures: int = 0,
    entitled_users=(),
    inactive_users=(),
    expired_users=(),
):
    database = tmp_path / "dispatch.db"
    history = InMemorySignalHistoryStore()
    signal = make_signal()
    signal_record = history.record(signal, "CREATED", NOW)
    event = make_event(signal_record.signal_id, signal)
    outbox = SQLiteAlertOutbox(database)
    outbox.publish(event)
    deliveries = SQLiteSignalAlertDeliveryStore(database)
    subscriptions = SQLiteSubscriptionStore(database)
    user_store = SQLiteUserStore(database)
    for account in accounts:
        status = UserStatus.DISABLED if account.user_id in inactive_users else UserStatus.ACTIVE
        user_store.save(User(id=account.user_id, status=status))
    subscriptions.save_plan(
        SubscriptionPlan(
            plan_id="plus",
            version=1,
            display_name="Plus",
            entitlements=(EntitlementGrant("telegram_opportunities", True, 100),),
            active=True,
            created_at=NOW,
        )
    )
    subscription_users = set(entitled_users) | set(expired_users)
    for user_id in subscription_users:
        is_expired = user_id in expired_users
        starts_at = NOW - timedelta(days=30) if is_expired else NOW
        expires_at = NOW - timedelta(seconds=1) if is_expired else NOW + timedelta(days=30)
        subscriptions.create(
            Subscription(
                subscription_id=uuid4(),
                user_id=user_id,
                plan_id="plus",
                plan_version=1,
                status=SubscriptionStatus.ACTIVE,
                created_at=NOW,
                starts_at=starts_at,
                expires_at=expires_at,
                updated_at=NOW,
            ),
            actor="test-billing",
            reason="Verified test subscription",
        )
    transport = FakeTransport(failures=failures, ambiguous_failures=ambiguous_failures)
    dispatcher = DispatchSignalAlertOutbox(
        outbox=outbox,
        recipients=FakeRecipients(accounts),
        deliveries=deliveries,
        users=user_store,
        history=history,
        entitlements=EntitlementEvaluator(subscriptions),
        transport=transport,
    )
    return dispatcher, outbox, deliveries, transport, event, history


def test_dispatch_sends_only_to_entitled_linked_recipients(tmp_path) -> None:
    entitled_user = uuid4()
    free_user = uuid4()
    dispatcher, outbox, deliveries, transport, event, history = setup_dispatch(
        tmp_path,
        [
            LinkedTelegramAccount(entitled_user, "chat-paid"),
            LinkedTelegramAccount(free_user, "chat-free"),
        ],
        entitled_users=(entitled_user,),
    )
    # A later lifecycle state must not rewrite the snapshot attached to this event.
    history.record(
        replace(make_signal(), status=SignalStatus.CLOSED),
        "STATUS_CLOSED",
        NOW + timedelta(minutes=1),
    )

    result = dispatcher.execute(now=NOW)

    assert result.events_processed == 1
    assert result.recipients_delivered == 1
    assert result.recipients_suppressed == 1
    assert result.recipients_failed == 0
    assert len(transport.sent) == 1
    chat_id, message = transport.sent[0]
    assert chat_id == "chat-paid"
    assert "Entry zone: 80 – 81" in message
    assert "Status: INVALIDATED" in message
    assert "Invalidation: 78" in message
    assert "T1: 85" in message
    assert "Targets:\n- T1: 85\n- T2: 88\nEvidence:\n- support_rejection: Rejected support" in message
    assert str(event.event_id) in message
    assert outbox.get(event.event_id).status.value == "DELIVERED"
    assert deliveries.get(event.event_id, entitled_user, "telegram").status is SignalAlertDeliveryStatus.DELIVERED
    assert deliveries.get(event.event_id, free_user, "telegram").status is SignalAlertDeliveryStatus.SUPPRESSED

    replay = dispatcher.execute(now=NOW + timedelta(minutes=1))
    assert replay.events_processed == 0
    assert len(transport.sent) == 1


def test_dispatch_retries_failed_recipient_without_resending_successes(tmp_path) -> None:
    first_user = uuid4()
    second_user = uuid4()
    dispatcher, outbox, deliveries, transport, event, _history = setup_dispatch(
        tmp_path,
        [
            LinkedTelegramAccount(first_user, "chat-1"),
            LinkedTelegramAccount(second_user, "chat-2"),
        ],
        failures=1,
        entitled_users=(first_user, second_user),
    )

    first = dispatcher.execute(now=NOW)
    assert first.recipients_delivered == 1
    assert first.recipients_failed == 1
    assert outbox.get(event.event_id).status.value == "FAILED"

    second = dispatcher.execute(now=NOW + timedelta(minutes=1))
    assert second.recipients_delivered == 1
    assert second.recipients_failed == 0
    assert len(transport.sent) == 2
    records = [
        deliveries.get(event.event_id, first_user, "telegram"),
        deliveries.get(event.event_id, second_user, "telegram"),
    ]
    assert all(record.status is SignalAlertDeliveryStatus.DELIVERED for record in records)
    assert sorted(record.attempts for record in records) == [1, 2]
    assert outbox.get(event.event_id).status.value == "DELIVERED"


def test_dispatch_fails_closed_when_no_plan_grants_access(tmp_path) -> None:
    user_id = uuid4()
    dispatcher, outbox, deliveries, transport, event, _history = setup_dispatch(
        tmp_path,
        [LinkedTelegramAccount(user_id, "chat-unentitled")],
    )

    result = dispatcher.execute(now=NOW)

    assert result.events_processed == 1
    assert result.events_suppressed_no_eligible_recipients == 1
    assert result.recipients_suppressed == 1
    assert transport.sent == []
    assert deliveries.get(event.event_id, user_id, "telegram").status is SignalAlertDeliveryStatus.SUPPRESSED
    record = outbox.get(event.event_id)
    assert record.status is AlertOutboxStatus.SUPPRESSED_NO_ELIGIBLE_RECIPIENTS
    assert record.last_error == "no eligible Telegram recipients at dispatch time"

    replay = dispatcher.execute(now=NOW + timedelta(minutes=1))
    assert replay.events_processed == 0
    assert transport.sent == []


def test_telegram_opportunity_message_respects_provider_length_limit() -> None:
    signal = replace(
        make_signal(),
        evidence=tuple(
            SignalEvidence(f"evidence-{index}", "supporting observation " * 100)
            for index in range(20)
        ),
    )
    event = make_event(uuid4())
    record = AlertOutboxRecord(
        event=event,
        status=AlertOutboxStatus.PENDING,
        attempts=0,
        created_at=NOW,
    )

    message = DispatchSignalAlertOutbox._format_message(record, snapshot_signal(signal))

    assert len(message) <= 3900
    assert str(event.event_id) in message
    assert "not proof of an executed trade" in message


def test_dispatch_suppresses_disabled_user_even_with_active_subscription(tmp_path) -> None:
    user_id = uuid4()
    dispatcher, outbox, deliveries, transport, event, _history = setup_dispatch(
        tmp_path,
        [LinkedTelegramAccount(user_id, "chat-disabled")],
        entitled_users=(user_id,),
        inactive_users=(user_id,),
    )

    result = dispatcher.execute(now=NOW)

    assert result.recipients_suppressed == 1
    assert result.events_suppressed_no_eligible_recipients == 1
    assert transport.sent == []
    record = deliveries.get(event.event_id, user_id, "telegram")
    assert record.status is SignalAlertDeliveryStatus.SUPPRESSED
    assert record.last_error == "user_inactive_or_missing"
    assert outbox.get(event.event_id).status is AlertOutboxStatus.SUPPRESSED_NO_ELIGIBLE_RECIPIENTS

def test_dispatch_suppresses_event_terminally_when_no_recipients_are_linked(tmp_path) -> None:
    dispatcher, outbox, deliveries, transport, event, _history = setup_dispatch(
        tmp_path,
        [],
    )

    result = dispatcher.execute(now=NOW)

    assert result.events_processed == 1
    assert result.events_suppressed_no_recipients == 1
    assert result.events_suppressed_no_eligible_recipients == 0
    assert result.recipients_delivered == 0
    assert result.recipients_suppressed == 0
    assert result.recipients_failed == 0
    assert transport.sent == []
    record = outbox.get(event.event_id)
    assert record.status is AlertOutboxStatus.SUPPRESSED_NO_RECIPIENTS
    assert record.last_error == "no linked Telegram recipients at dispatch time"
    with sqlite3.connect(tmp_path / "dispatch.db") as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM signal_alert_deliveries WHERE event_id = ?",
            (str(event.event_id),),
        ).fetchone()[0]
    assert count == 0

def test_published_opportunity_reaches_entitled_telegram_recipient_once(tmp_path) -> None:
    from app.application.alerts.publish_signal_opportunity import PublishSignalOpportunity

    database = tmp_path / "publication-dispatch.db"
    history = InMemorySignalHistoryStore()
    outbox = SQLiteAlertOutbox(database)
    publisher = PublishSignalOpportunity(history=history, outbox=outbox)
    signal = make_signal()

    publication = publisher.execute(signal, recorded_at=NOW)
    assert publication is not None
    assert publication.queued_new_event is True

    user_id = uuid4()
    users = SQLiteUserStore(database)
    users.save(User(id=user_id, status=UserStatus.ACTIVE))
    subscriptions = SQLiteSubscriptionStore(database)
    subscriptions.save_plan(
        SubscriptionPlan(
            plan_id="plus",
            version=1,
            display_name="Plus",
            entitlements=(EntitlementGrant("telegram_opportunities", True, 100),),
            active=True,
            created_at=NOW,
        )
    )
    subscriptions.create(
        Subscription(
            subscription_id=uuid4(),
            user_id=user_id,
            plan_id="plus",
            plan_version=1,
            status=SubscriptionStatus.ACTIVE,
            created_at=NOW,
            starts_at=NOW,
            expires_at=NOW + timedelta(days=30),
            updated_at=NOW,
        ),
        actor="test-billing",
        reason="Verified test subscription",
    )
    transport = FakeTransport()
    dispatcher = DispatchSignalAlertOutbox(
        outbox=outbox,
        recipients=FakeRecipients([LinkedTelegramAccount(user_id, "chat-paid")]),
        deliveries=SQLiteSignalAlertDeliveryStore(database),
        users=users,
        history=history,
        entitlements=EntitlementEvaluator(subscriptions),
        transport=transport,
    )

    first_dispatch = dispatcher.execute(now=NOW)
    replay_publication = publisher.execute(
        signal,
        recorded_at=NOW + timedelta(minutes=1),
    )
    replay_dispatch = dispatcher.execute(now=NOW + timedelta(minutes=1))

    assert first_dispatch.events_processed == 1
    assert first_dispatch.recipients_delivered == 1
    assert replay_publication is not None
    assert replay_publication.event_id == publication.event_id
    assert replay_publication.queued_new_event is False
    assert replay_dispatch.events_processed == 0
    assert len(transport.sent) == 1
    assert transport.sent[0][0] == "chat-paid"
    assert "Update: COMI opportunity published from price-action v1" in transport.sent[0][1]
    assert outbox.get(publication.event_id).status is AlertOutboxStatus.DELIVERED



def test_dispatch_suppresses_expired_subscription_before_telegram_send(tmp_path) -> None:
    expired_user = uuid4()
    dispatcher, outbox, deliveries, transport, event, _history = setup_dispatch(
        tmp_path,
        [LinkedTelegramAccount(expired_user, "chat-expired")],
        expired_users=(expired_user,),
    )

    result = dispatcher.execute(now=NOW)

    assert result.events_processed == 1
    assert result.recipients_delivered == 0
    assert result.recipients_suppressed == 1
    assert result.recipients_failed == 0
    assert transport.sent == []
    delivery = deliveries.get(event.event_id, expired_user, "telegram")
    assert delivery is not None
    assert delivery.status is SignalAlertDeliveryStatus.SUPPRESSED
    assert delivery.last_error == "no_eligible_plan"
    assert outbox.get(event.event_id).status is AlertOutboxStatus.SUPPRESSED_NO_ELIGIBLE_RECIPIENTS


def test_ambiguous_transport_outcome_is_not_automatically_retried(tmp_path) -> None:
    user_id = uuid4()
    dispatcher, outbox, deliveries, transport, event, _history = setup_dispatch(
        tmp_path,
        [LinkedTelegramAccount(user_id, "chat-ambiguous")],
        ambiguous_failures=1,
        entitled_users=(user_id,),
    )

    first = dispatcher.execute(now=NOW)
    delivery = deliveries.get(event.event_id, user_id, "telegram")
    assert first.recipients_delivered == 0
    assert first.recipients_failed == 0
    assert delivery is not None
    assert delivery.status is SignalAlertDeliveryStatus.DELIVERY_UNKNOWN
    assert outbox.get(event.event_id).status is AlertOutboxStatus.PENDING
    assert transport.sent == []

    second = dispatcher.execute(now=NOW + timedelta(minutes=1))
    assert second.events_processed == 1
    assert transport.sent == []
    assert deliveries.get(event.event_id, user_id, "telegram").status is SignalAlertDeliveryStatus.DELIVERY_UNKNOWN
    # Unknown delivery keeps the event unresolved rather than falsely suppressing
    # or marking it delivered.
    assert outbox.get(event.event_id).status is AlertOutboxStatus.PENDING
