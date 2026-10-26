from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.subscriptions.model import (
    EntitlementGrant,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from app.infrastructure.persistence.sqlite_subscription_store import SQLiteSubscriptionStore


NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def make_plan(
    *,
    version: int = 1,
    active: bool = True,
    entitlements=(EntitlementGrant("opportunities", True, 10),),
) -> SubscriptionPlan:
    return SubscriptionPlan(
        plan_id="plus",
        version=version,
        display_name="Plus",
        entitlements=entitlements,
        active=active,
        created_at=NOW,
    )


def make_subscription(
    user_id,
    *,
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
    created_at: datetime = NOW,
    starts_at: datetime = NOW,
    expires_at: datetime = NOW + timedelta(days=30),
    payment_reference: str | None = None,
) -> Subscription:
    return Subscription(
        subscription_id=uuid4(),
        user_id=user_id,
        plan_id="plus",
        plan_version=1,
        status=status,
        created_at=created_at,
        starts_at=starts_at,
        expires_at=expires_at,
        updated_at=created_at,
        payment_provider="test-gateway" if payment_reference else None,
        payment_reference=payment_reference,
    )


def test_plan_versions_are_immutable_and_restart_safe(tmp_path) -> None:
    database = tmp_path / "subscriptions.db"
    store = SQLiteSubscriptionStore(database)
    plan = make_plan()
    store.save_plan(plan)
    store.save_plan(plan)
    reopened = SQLiteSubscriptionStore(database)

    assert reopened.get_plan("plus", 1) == plan
    with pytest.raises(ValueError, match="immutable"):
        reopened.save_plan(
            make_plan(entitlements=(EntitlementGrant("opportunities", True, 20),))
        )


def test_subscription_create_and_status_transitions_are_audited(tmp_path) -> None:
    database = tmp_path / "subscriptions.db"
    store = SQLiteSubscriptionStore(database)
    store.save_plan(make_plan())
    user_id = uuid4()
    subscription = make_subscription(user_id)
    store.create(subscription, actor="billing-reconciler", reason="Verified payment")

    changed = store.transition(
        subscription.subscription_id,
        SubscriptionStatus.PAST_DUE,
        occurred_at=NOW + timedelta(days=1),
        actor="billing-reconciler",
        reason="Renewal payment failed",
    )
    assert changed.status is SubscriptionStatus.PAST_DUE
    assert store.get(subscription.subscription_id) == changed

    restored = store.transition(
        subscription.subscription_id,
        SubscriptionStatus.ACTIVE,
        occurred_at=NOW + timedelta(days=2),
        actor="billing-reconciler",
        reason="Payment reconciled",
    )
    assert restored.status is SubscriptionStatus.ACTIVE
    with store._connect() as connection:
        events = connection.execute(
            "SELECT event, previous_status, new_status FROM subscription_events ORDER BY id"
        ).fetchall()
    assert events == [
        ("SUBSCRIPTION_CREATED", None, "ACTIVE"),
        ("STATUS_TRANSITION", "ACTIVE", "PAST_DUE"),
        ("STATUS_TRANSITION", "PAST_DUE", "ACTIVE"),
    ]


def test_subscription_rejects_invalid_lifecycle_transition(tmp_path) -> None:
    store = SQLiteSubscriptionStore(tmp_path / "subscriptions.db")
    store.save_plan(make_plan())
    subscription = make_subscription(uuid4(), status=SubscriptionStatus.CANCELLED)
    store.create(subscription, actor="test", reason="Fixture")

    with pytest.raises(ValueError, match="Transition from CANCELLED to ACTIVE is not allowed"):
        store.transition(
            subscription.subscription_id,
            SubscriptionStatus.ACTIVE,
            occurred_at=NOW + timedelta(days=1),
            actor="test",
            reason="Must not reopen cancelled subscription",
        )


def test_current_subscription_query_uses_valid_time_window(tmp_path) -> None:
    store = SQLiteSubscriptionStore(tmp_path / "subscriptions.db")
    store.save_plan(make_plan())
    user_id = uuid4()
    expired = make_subscription(
        user_id,
        created_at=NOW - timedelta(days=60),
        starts_at=NOW - timedelta(days=60),
        expires_at=NOW - timedelta(days=30),
    )
    future = make_subscription(
        user_id,
        created_at=NOW,
        starts_at=NOW + timedelta(days=1),
        expires_at=NOW + timedelta(days=31),
    )
    store.create(expired, actor="test", reason="Expired fixture")
    store.create(future, actor="test", reason="Future fixture")

    assert store.current_for_user(user_id, now=NOW) is None
    assert store.latest_for_user(user_id) == future


def test_payment_reference_is_unique_per_provider(tmp_path) -> None:
    store = SQLiteSubscriptionStore(tmp_path / "subscriptions.db")
    store.save_plan(make_plan())
    store.save_plan(
        SubscriptionPlan(
            plan_id="basic",
            version=1,
            display_name="Basic",
            entitlements=(),
            active=True,
            created_at=NOW,
        )
    )
    store.create(
        make_subscription(uuid4(), payment_reference="provider-ref-1"),
        actor="billing",
        reason="First payment",
    )
    second = Subscription(
        subscription_id=uuid4(),
        user_id=uuid4(),
        plan_id="basic",
        plan_version=1,
        status=SubscriptionStatus.ACTIVE,
        created_at=NOW,
        starts_at=NOW,
        expires_at=NOW + timedelta(days=30),
        updated_at=NOW,
        payment_provider="test-gateway",
        payment_reference="provider-ref-1",
    )

    with pytest.raises(Exception):
        store.create(second, actor="billing", reason="Duplicate payment reference")
