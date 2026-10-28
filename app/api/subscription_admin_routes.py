from __future__ import annotations

from datetime import datetime, timezone
from sqlite3 import IntegrityError
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.application.identity.user_store import UserStore
from app.application.security.identity import AuthenticatedIdentity
from app.application.subscriptions.store import SubscriptionStore
from app.domain.subscriptions.model import (
    EntitlementGrant as PlanEntitlementGrant,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)


class PlanEntitlementPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    limit: int | None = Field(default=None, ge=0)


class SubscriptionPlanPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)
    display_name: str = Field(min_length=1, max_length=200)
    entitlements: list[PlanEntitlementPayload]
    active: bool = True
    created_at: datetime | None = None


class SubscriptionCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    plan_id: str = Field(min_length=1, max_length=100)
    plan_version: int = Field(ge=1)
    starts_at: datetime
    expires_at: datetime
    reason: str = Field(min_length=1, max_length=500)
    payment_provider: str | None = Field(default=None, max_length=100)
    payment_reference: str | None = Field(default=None, max_length=250)


class SubscriptionTransitionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SubscriptionStatus
    reason: str = Field(min_length=1, max_length=500)


def _require_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(status_code=422, detail=f"{field} must include a timezone")


def _plan_payload(plan: SubscriptionPlan) -> dict[str, object]:
    return {
        "plan_id": plan.plan_id,
        "version": plan.version,
        "display_name": plan.display_name,
        "active": plan.active,
        "created_at": plan.created_at.isoformat(),
        "entitlements": [
            {"code": item.code, "enabled": item.enabled, "limit": item.limit}
            for item in plan.entitlements
        ],
    }


def _subscription_payload(subscription: Subscription) -> dict[str, object]:
    return {
        "subscription_id": str(subscription.subscription_id),
        "user_id": str(subscription.user_id),
        "plan_id": subscription.plan_id,
        "plan_version": subscription.plan_version,
        "status": subscription.status.value,
        "created_at": subscription.created_at.isoformat(),
        "starts_at": subscription.starts_at.isoformat(),
        "expires_at": subscription.expires_at.isoformat(),
        "updated_at": subscription.updated_at.isoformat(),
        "payment_provider": subscription.payment_provider,
        "payment_reference": subscription.payment_reference,
    }


def create_subscription_admin_router(
    *,
    store: SubscriptionStore | None,
    users: UserStore | None,
    require_operator,
) -> APIRouter:
    """Expose audited, operator-only subscription administration without billing claims."""
    router = APIRouter()

    def configured_store() -> SubscriptionStore:
        if store is None:
            raise HTTPException(status_code=503, detail="Subscription management is not configured")
        return store

    @router.post("/api/v1/owner/subscription-plans")
    def create_subscription_plan(
        payload: SubscriptionPlanPayload,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        subscription_store = configured_store()
        created_at = payload.created_at or datetime.now(timezone.utc)
        _require_aware(created_at, "created_at")
        try:
            plan = SubscriptionPlan(
                plan_id=payload.plan_id.strip(),
                version=payload.version,
                display_name=payload.display_name.strip(),
                entitlements=tuple(
                    PlanEntitlementGrant(
                        code=item.code.strip(),
                        enabled=item.enabled,
                        limit=item.limit,
                    )
                    for item in payload.entitlements
                ),
                active=payload.active,
                created_at=created_at,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        try:
            subscription_store.save_plan(plan)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return _plan_payload(plan)

    @router.get("/api/v1/owner/subscription-plans/{plan_id}/{version}")
    def get_subscription_plan(
        plan_id: str,
        version: int,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        subscription_store = configured_store()
        plan = subscription_store.get_plan(plan_id, version)
        if plan is None:
            raise HTTPException(status_code=404, detail="Subscription plan version not found")
        return _plan_payload(plan)

    @router.post("/api/v1/owner/subscriptions")
    def create_subscription(
        payload: SubscriptionCreatePayload,
        identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        subscription_store = configured_store()
        _require_aware(payload.starts_at, "starts_at")
        _require_aware(payload.expires_at, "expires_at")
        if users is None:
            raise HTTPException(status_code=503, detail="User directory is not configured")
        if users.get(payload.user_id) is None:
            raise HTTPException(status_code=404, detail="User not found")
        plan_id = payload.plan_id.strip()
        plan = subscription_store.get_plan(plan_id, payload.plan_version)
        if plan is None:
            raise HTTPException(status_code=422, detail="Subscription plan version does not exist")
        if not plan.active:
            raise HTTPException(status_code=409, detail="Inactive subscription plans cannot be provisioned")

        now = datetime.now(timezone.utc)
        actor = identity.subject.strip() or "operator"
        reason = payload.reason.strip()
        if not reason:
            raise HTTPException(status_code=422, detail="reason is required")
        try:
            subscription = Subscription(
                subscription_id=uuid4(),
                user_id=payload.user_id,
                plan_id=plan_id,
                plan_version=payload.plan_version,
                status=SubscriptionStatus.PENDING,
                created_at=now,
                starts_at=payload.starts_at,
                expires_at=payload.expires_at,
                updated_at=now,
                payment_provider=payload.payment_provider.strip() if payload.payment_provider else None,
                payment_reference=payload.payment_reference.strip() if payload.payment_reference else None,
            )
            subscription_store.create(subscription, actor=actor, reason=reason)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except IntegrityError as error:
            # Keep database/driver details out of the API response.
            raise HTTPException(status_code=409, detail="Subscription could not be created; verify the plan version and payment-reference uniqueness") from error
        return _subscription_payload(subscription)

    @router.get("/api/v1/owner/subscriptions/{subscription_id}")
    def get_subscription(
        subscription_id: UUID,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        subscription_store = configured_store()
        subscription = subscription_store.get(subscription_id)
        if subscription is None:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return _subscription_payload(subscription)

    @router.get("/api/v1/owner/subscriptions/{subscription_id}/events")
    def get_subscription_events(
        subscription_id: UUID,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        subscription_store = configured_store()
        if subscription_store.get(subscription_id) is None:
            raise HTTPException(status_code=404, detail="Subscription not found")
        events = subscription_store.events_for_subscription(subscription_id)
        return {
            "subscription_id": str(subscription_id),
            "events": [
                {
                    "event_id": item.event_id,
                    "actor": item.actor,
                    "event": item.event,
                    "reason": item.reason,
                    "occurred_at": item.occurred_at.isoformat(),
                    "previous_status": item.previous_status.value if item.previous_status else None,
                    "new_status": item.new_status.value,
                }
                for item in events
            ],
        }

    @router.get("/api/v1/owner/subscriptions/by-user/{user_id}/latest")
    def get_latest_user_subscription(
        user_id: UUID,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        subscription_store = configured_store()
        subscription = subscription_store.latest_for_user(user_id)
        if subscription is None:
            raise HTTPException(status_code=404, detail="Subscription not found for user")
        return _subscription_payload(subscription)

    @router.post("/api/v1/owner/subscriptions/{subscription_id}/transition")
    def transition_subscription(
        subscription_id: UUID,
        payload: SubscriptionTransitionPayload,
        identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        subscription_store = configured_store()
        now = datetime.now(timezone.utc)
        actor = str(identity.user_id) if identity.user_id is not None else "operator"
        reason = payload.reason.strip()
        if not reason:
            raise HTTPException(status_code=422, detail="reason is required")
        try:
            subscription = subscription_store.transition(
                subscription_id,
                payload.status,
                occurred_at=now,
                actor=actor,
                reason=reason,
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except LookupError as error:
            raise HTTPException(status_code=404, detail="Subscription not found") from error
        return _subscription_payload(subscription)

    return router
