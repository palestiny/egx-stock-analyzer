from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class SubscriptionStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    REFUNDED = "REFUNDED"


@dataclass(frozen=True)
class EntitlementGrant:
    code: str
    enabled: bool = True
    limit: int | None = None

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("entitlement code is required")
        if self.limit is not None and self.limit < 0:
            raise ValueError("entitlement limit cannot be negative")


@dataclass(frozen=True)
class SubscriptionPlan:
    plan_id: str
    version: int
    display_name: str
    entitlements: tuple[EntitlementGrant, ...]
    active: bool
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.plan_id.strip():
            raise ValueError("plan ID is required")
        if self.version < 1:
            raise ValueError("plan version must be positive")
        if not self.display_name.strip():
            raise ValueError("plan display name is required")
        if len({grant.code for grant in self.entitlements}) != len(self.entitlements):
            raise ValueError("entitlement codes must be unique within a plan")
        _require_aware(self.created_at, "created_at")


@dataclass(frozen=True)
class Subscription:
    subscription_id: UUID
    user_id: UUID
    plan_id: str
    plan_version: int
    status: SubscriptionStatus
    created_at: datetime
    starts_at: datetime
    expires_at: datetime
    updated_at: datetime
    payment_provider: str | None = None
    payment_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.plan_id.strip():
            raise ValueError("subscription plan ID is required")
        if self.plan_version < 1:
            raise ValueError("subscription plan version must be positive")
        for name, value in (
            ("created_at", self.created_at),
            ("starts_at", self.starts_at),
            ("expires_at", self.expires_at),
            ("updated_at", self.updated_at),
        ):
            _require_aware(value, name)
        if self.expires_at <= self.starts_at:
            raise ValueError("subscription expiry must be after its start")
        if self.updated_at < self.created_at:
            raise ValueError("subscription update time cannot precede creation")
        if (self.payment_provider is None) != (self.payment_reference is None):
            raise ValueError("payment provider and reference must be supplied together")
        if self.payment_provider is not None and not self.payment_provider.strip():
            raise ValueError("payment provider cannot be empty")
        if self.payment_reference is not None and not self.payment_reference.strip():
            raise ValueError("payment reference cannot be empty")

    def transition_to(
        self,
        new_status: SubscriptionStatus,
        *,
        occurred_at: datetime,
    ) -> Subscription:
        _require_aware(occurred_at, "occurred_at")
        if occurred_at < self.updated_at:
            raise ValueError("subscription transition time cannot move backwards")
        allowed = {
            SubscriptionStatus.PENDING: {
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.CANCELLED,
                SubscriptionStatus.EXPIRED,
                SubscriptionStatus.REFUNDED,
            },
            SubscriptionStatus.ACTIVE: {
                SubscriptionStatus.PAST_DUE,
                SubscriptionStatus.CANCELLED,
                SubscriptionStatus.EXPIRED,
                SubscriptionStatus.REFUNDED,
            },
            SubscriptionStatus.PAST_DUE: {
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.CANCELLED,
                SubscriptionStatus.EXPIRED,
                SubscriptionStatus.REFUNDED,
            },
            SubscriptionStatus.CANCELLED: set(),
            SubscriptionStatus.EXPIRED: set(),
            SubscriptionStatus.REFUNDED: set(),
        }
        if new_status not in allowed[self.status]:
            raise ValueError(
                f"Transition from {self.status.value} to {new_status.value} is not allowed"
            )
        return replace(self, status=new_status, updated_at=occurred_at)

    def grants_access_at(self, now: datetime) -> bool:
        _require_aware(now, "now")
        return (
            self.status is SubscriptionStatus.ACTIVE
            and self.starts_at <= now < self.expires_at
        )


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
