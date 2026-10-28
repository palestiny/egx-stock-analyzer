from __future__ import annotations

from datetime import datetime, timezone
from sqlite3 import IntegrityError
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.application.identity.user_store import UserStore
from app.application.security.identity import AuthenticatedIdentity
from app.application.subscriptions.manage_subscriptions import (
    InactiveSubscriptionPlan,
    SubscriptionAdministration,
    SubscriptionPlanNotFound,
    SubscriptionPlanVersionConflict,
    SubscriptionUserNotFound,
)
from app.application.subscriptions.store import SubscriptionStore
from app.domain.subscriptions.model import (
    EntitlementGrant as PlanEntitlementGrant,
    Subscription,
    SubscriptionEvent,
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


def _subscription_event_payload(event: SubscriptionEvent) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "subscription_id": str(event.subscription_id),
        "actor": event.actor,
        "event": event.event,
        "reason": event.reason,
        "occurred_at": event.occurred_at.isoformat(),
        "previous_status": event.previous_status.value if event.previous_status is not None else None,
        "new_status": event.new_status.value,
    }


def create_subscription_admin_router(
    *,
    store: SubscriptionStore | None,
    users: UserStore | None,
    require_operator,
) -> APIRouter:
    """Expose restricted operator routes while keeping business rules in application services."""
    router = APIRouter()

    def configured_service() -> SubscriptionAdministration:
        if store is None:
            raise HTTPException(status_code=503, detail="Subscription management is not configured")
        return SubscriptionAdministration(store, users)

    @router.post("/api/v1/owner/subscription-plans")
    def create_subscription_plan(
        payload: SubscriptionPlanPayload,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        service = configured_service()
        created_at = payload.created_at or datetime.now(timezone.utc)
        _require_aware(created_at, "created_at")
        try:
            entitlements = tuple(
                PlanEntitlementGrant(
                    code=item.code.strip(),
                    enabled=item.enabled,
                    limit=item.limit,
                )
                for item in payload.entitlements
            )
            plan = service.create_plan(
                plan_id=payload.plan_id,
                version=payload.version,
                display_name=payload.display_name,
                entitlements=entitlements,
                active=payload.active,
                created_at=created_at,
            )
        except SubscriptionPlanVersionConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except IntegrityError as error:
            raise HTTPException(
                status_code=409,
                detail="Subscription plan version already exists or conflicts with a concurrent creation",
            ) from error
        return _plan_payload(plan)

    @router.get("/api/v1/owner/subscription-plans/{plan_id}/{version}")
    def get_subscription_plan(
        plan_id: str,
        version: int,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        plan = configured_service().get_plan(plan_id, version)
        if plan is None:
            raise HTTPException(status_code=404, detail="Subscription plan version not found")
        return _plan_payload(plan)

    @router.post("/api/v1/owner/subscriptions")
    def create_subscription(
        payload: SubscriptionCreatePayload,
        identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        service = configured_service()
        _require_aware(payload.starts_at, "starts_at")
        _require_aware(payload.expires_at, "expires_at")
        reason = payload.reason.strip()
        if not reason:
            raise HTTPException(status_code=422, detail="reason is required")
        actor = identity.subject.strip() or "operator"
        try:
            subscription = service.provision(
                user_id=payload.user_id,
                plan_id=payload.plan_id,
                plan_version=payload.plan_version,
                starts_at=payload.starts_at,
                expires_at=payload.expires_at,
                actor=actor,
                reason=reason,
                payment_provider=payload.payment_provider,
                payment_reference=payload.payment_reference,
            )
        except RuntimeError as error:
            if "user directory is not configured" not in str(error):
                raise
            raise HTTPException(status_code=503, detail="User directory is not configured") from error
        except SubscriptionUserNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except SubscriptionPlanNotFound as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except InactiveSubscriptionPlan as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except IntegrityError as error:
            raise HTTPException(
                status_code=409,
                detail="Subscription could not be created; verify the plan version and payment-reference uniqueness",
            ) from error
        return _subscription_payload(subscription)

    @router.get("/api/v1/owner/subscriptions/{subscription_id}")
    def get_subscription(
        subscription_id: UUID,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        subscription = configured_service().get_subscription(subscription_id)
        if subscription is None:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return _subscription_payload(subscription)

    @router.get("/api/v1/owner/subscriptions/by-user/{user_id}/latest")
    def get_latest_user_subscription(
        user_id: UUID,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        subscription = configured_service().latest_for_user(user_id)
        if subscription is None:
            raise HTTPException(status_code=404, detail="Subscription not found for user")
        return _subscription_payload(subscription)

    @router.get("/api/v1/owner/subscriptions/{subscription_id}/events")
    def get_subscription_events(
        subscription_id: UUID,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        try:
            events = configured_service().events_for_subscription(subscription_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return {
            "subscription_id": str(subscription_id),
            "events": [_subscription_event_payload(event) for event in events],
        }

    @router.post("/api/v1/owner/subscriptions/{subscription_id}/transition")
    def transition_subscription(
        subscription_id: UUID,
        payload: SubscriptionTransitionPayload,
        identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        reason = payload.reason.strip()
        if not reason:
            raise HTTPException(status_code=422, detail="reason is required")
        actor = identity.subject.strip() or "operator"
        try:
            subscription = configured_service().transition(
                subscription_id,
                payload.status,
                actor=actor,
                reason=reason,
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RuntimeError as error:
            if "changed concurrently" not in str(error):
                raise
            raise HTTPException(
                status_code=409,
                detail="Subscription changed concurrently; reload before retrying",
            ) from error
        return _subscription_payload(subscription)

    return router
