from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.application.subscriptions.entitlement_evaluator import EntitlementEvaluator
from app.domain.subscriptions.model import (
    EntitlementGrant,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from app.infrastructure.persistence.sqlite_subscription_store import SQLiteSubscriptionStore


NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def plan(
    plan_id: str,
    version: int = 1,
    *,
    active: bool = True,
    entitlements=(EntitlementGrant("telegram_opportunities", True, 20),),
) -> SubscriptionPlan:
    return SubscriptionPlan(
        plan_id=plan_id,
        version=version,
        display_name=plan_id.title(),
        entitlements=entitlements,
        active=active,
        created_at=NOW,
    )


def subscription(user_id, plan_id: str = "plus", status=SubscriptionStatus.ACTIVE):
    return Subscription(
        subscription_id=uuid4(),
        user_id=user_id,
        plan_id=plan_id,
        plan_version=1,
        status=status,
        created_at=NOW,
        starts_at=NOW,
        expires_at=NOW + timedelta(days=30),
        updated_at=NOW,
    )


def test_evaluator_grants_entitlement_from_active_versioned_plan(tmp_path) -> None:
    store = SQLiteSubscriptionStore(tmp_path / "subscriptions.db")
    store.save_plan(plan("plus"))
    user_id = uuid4()
    active = subscription(user_id)
    store.create(active, actor="billing", reason="Verified entitlement fixture")
    evaluator = EntitlementEvaluator(store)

    decision = evaluator.evaluate(
        user_id,
        "telegram_opportunities",
        now=NOW + timedelta(days=1),
    )

    assert decision.allowed is True
    assert decision.reason == "granted"
    assert decision.plan_id == "plus"
    assert decision.plan_version == 1
    assert decision.limit == 20


def test_evaluator_uses_configured_default_plan_without_subscription(tmp_path) -> None:
    store = SQLiteSubscriptionStore(tmp_path / "subscriptions.db")
    store.save_plan(
        plan("free", entitlements=(EntitlementGrant("session_summary", True, 1),))
    )
    evaluator = EntitlementEvaluator(
        store,
        default_plan_id="free",
        default_plan_version=1,
    )

    decision = evaluator.evaluate(
        uuid4(),
        "session_summary",
        now=NOW,
    )

    assert decision.allowed is True
    assert decision.plan_id == "free"
    assert decision.limit == 1


def test_evaluator_denies_ungranted_and_inactive_plan_entitlements(tmp_path) -> None:
    store = SQLiteSubscriptionStore(tmp_path / "subscriptions.db")
    store.save_plan(
        plan("plus", entitlements=(EntitlementGrant("telegram_opportunities", False),))
    )
    user_id = uuid4()
    store.create(subscription(user_id), actor="billing", reason="Test")
    evaluator = EntitlementEvaluator(store)

    decision = evaluator.evaluate(user_id, "telegram_opportunities", now=NOW)

    assert decision.allowed is False
    assert decision.reason == "entitlement_not_granted"


def test_evaluator_falls_back_to_default_when_subscription_is_expired(tmp_path) -> None:
    store = SQLiteSubscriptionStore(tmp_path / "subscriptions.db")
    store.save_plan(plan("free", entitlements=(EntitlementGrant("session_summary"),)))
    store.save_plan(plan("plus"))
    user_id = uuid4()
    expired = Subscription(
        subscription_id=uuid4(),
        user_id=user_id,
        plan_id="plus",
        plan_version=1,
        status=SubscriptionStatus.ACTIVE,
        created_at=NOW - timedelta(days=60),
        starts_at=NOW - timedelta(days=60),
        expires_at=NOW - timedelta(days=1),
        updated_at=NOW - timedelta(days=60),
    )
    store.create(expired, actor="billing", reason="Expired fixture")
    evaluator = EntitlementEvaluator(
        store,
        default_plan_id="free",
        default_plan_version=1,
    )

    free_decision = evaluator.evaluate(user_id, "session_summary", now=NOW)
    paid_decision = evaluator.evaluate(user_id, "telegram_opportunities", now=NOW)

    assert free_decision.allowed is True
    assert free_decision.plan_id == "free"
    assert paid_decision.allowed is False
    assert paid_decision.reason == "entitlement_not_granted"


def test_evaluator_fails_closed_without_plan_or_with_naive_time(tmp_path) -> None:
    store = SQLiteSubscriptionStore(tmp_path / "subscriptions.db")
    evaluator = EntitlementEvaluator(store)

    denied = evaluator.evaluate(uuid4(), "telegram_opportunities", now=NOW)
    assert denied.allowed is False
    assert denied.reason == "no_eligible_plan"

    with pytest.raises(ValueError, match="timezone-aware"):
        evaluator.evaluate(
            uuid4(),
            "telegram_opportunities",
            now=datetime(2026, 10, 26, 12, 0),
        )


def test_evaluator_requires_default_plan_identity_as_a_pair(tmp_path) -> None:
    store = SQLiteSubscriptionStore(tmp_path / "subscriptions.db")

    with pytest.raises(ValueError, match="supplied together"):
        EntitlementEvaluator(store, default_plan_id="free")
