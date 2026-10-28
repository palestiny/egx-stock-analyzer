from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.application.identity.user_store import UserStore
from app.application.subscriptions.store import SubscriptionStore
from app.domain.subscriptions.model import (
    EntitlementGrant,
    Subscription,
    SubscriptionEvent,
    SubscriptionPlan,
    SubscriptionStatus,
)


class SubscriptionPlanVersionConflict(Exception):
    """Raised when an immutable plan version already exists with other content."""


class SubscriptionAdministration:
    """Application use cases for operator-managed subscription plans and lifecycle."""

    def __init__(self, store: SubscriptionStore, users: UserStore | None) -> None:
        self._store = store
        self._users = users

    def create_plan(
        self,
        *,
        plan_id: str,
        version: int,
        display_name: str,
        entitlements: tuple[EntitlementGrant, ...],
        active: bool,
        created_at: datetime | None = None,
    ) -> SubscriptionPlan:
        plan = SubscriptionPlan(
            plan_id=plan_id.strip(),
            version=version,
            display_name=display_name.strip(),
            entitlements=entitlements,
            active=active,
            created_at=created_at or datetime.now(timezone.utc),
        )
        try:
            self._store.save_plan(plan)
        except ValueError as error:
            raise SubscriptionPlanVersionConflict(str(error)) from error
        return plan

    def provision(
        self,
        *,
        user_id: UUID,
        plan_id: str,
        plan_version: int,
        starts_at: datetime,
        expires_at: datetime,
        actor: str,
        reason: str,
        payment_provider: str | None = None,
        payment_reference: str | None = None,
    ) -> Subscription:
        if self._users is None:
            raise RuntimeError("user directory is not configured")
        if self._users.get(user_id) is None:
            raise LookupError("User not found")

        normalized_plan_id = plan_id.strip()
        plan = self._store.get_plan(normalized_plan_id, plan_version)
        if plan is None:
            raise LookupError("Subscription plan version does not exist")
        if not plan.active:
            raise ValueError("Inactive subscription plans cannot be provisioned")

        now = datetime.now(timezone.utc)
        subscription = Subscription(
            subscription_id=uuid4(),
            user_id=user_id,
            plan_id=normalized_plan_id,
            plan_version=plan_version,
            status=SubscriptionStatus.PENDING,
            created_at=now,
            starts_at=starts_at,
            expires_at=expires_at,
            updated_at=now,
            payment_provider=payment_provider.strip() if payment_provider else None,
            payment_reference=payment_reference.strip() if payment_reference else None,
        )
        self._store.create(subscription, actor=actor, reason=reason)
        return subscription

    def get_plan(self, plan_id: str, version: int) -> SubscriptionPlan | None:
        return self._store.get_plan(plan_id, version)

    def get_subscription(self, subscription_id: UUID) -> Subscription | None:
        return self._store.get(subscription_id)

    def latest_for_user(self, user_id: UUID) -> Subscription | None:
        return self._store.latest_for_user(user_id)

    def events_for_subscription(self, subscription_id: UUID) -> tuple[SubscriptionEvent, ...]:
        if self._store.get(subscription_id) is None:
            raise LookupError("Subscription not found")
        return self._store.events_for_subscription(subscription_id)

    def transition(
        self,
        subscription_id: UUID,
        status: SubscriptionStatus,
        *,
        actor: str,
        reason: str,
    ) -> Subscription:
        return self._store.transition(
            subscription_id,
            status,
            occurred_at=datetime.now(timezone.utc),
            actor=actor,
            reason=reason,
        )
