from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.subscriptions.store import SubscriptionStore
from app.domain.subscriptions.model import SubscriptionPlan


@dataclass(frozen=True)
class EntitlementDecision:
    allowed: bool
    reason: str
    plan_id: str | None
    plan_version: int | None
    entitlement_code: str
    limit: int | None = None


class EntitlementEvaluator:
    """Evaluate server-side feature access using versioned plan snapshots."""

    def __init__(
        self,
        store: SubscriptionStore,
        *,
        default_plan_id: str | None = None,
        default_plan_version: int | None = None,
    ) -> None:
        if (default_plan_id is None) != (default_plan_version is None):
            raise ValueError("default plan ID and version must be supplied together")
        if default_plan_id is not None and not default_plan_id.strip():
            raise ValueError("default plan ID cannot be empty")
        if default_plan_version is not None and default_plan_version < 1:
            raise ValueError("default plan version must be positive")
        self._store = store
        self._default_plan_id = default_plan_id
        self._default_plan_version = default_plan_version

    def evaluate(
        self,
        user_id: UUID,
        entitlement_code: str,
        *,
        now: datetime,
    ) -> EntitlementDecision:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        normalized_code = entitlement_code.strip()
        if not normalized_code:
            raise ValueError("entitlement code is required")

        subscription = self._store.latest_for_user(user_id)
        plan: SubscriptionPlan | None = None
        if subscription is not None and subscription.grants_access_at(now):
            plan = self._store.get_plan(
                subscription.plan_id,
                subscription.plan_version,
            )

        if plan is None and self._default_plan_id is not None:
            assert self._default_plan_version is not None
            plan = self._store.get_plan(
                self._default_plan_id,
                self._default_plan_version,
            )

        if plan is None:
            return EntitlementDecision(
                False,
                "no_eligible_plan",
                None,
                None,
                normalized_code,
            )
        if not plan.active:
            return EntitlementDecision(
                False,
                "plan_inactive",
                plan.plan_id,
                plan.version,
                normalized_code,
            )

        grant = next(
            (item for item in plan.entitlements if item.code == normalized_code),
            None,
        )
        if grant is None or not grant.enabled:
            return EntitlementDecision(
                False,
                "entitlement_not_granted",
                plan.plan_id,
                plan.version,
                normalized_code,
                grant.limit if grant is not None else None,
            )

        return EntitlementDecision(
            True,
            "granted",
            plan.plan_id,
            plan.version,
            normalized_code,
            grant.limit,
        )
