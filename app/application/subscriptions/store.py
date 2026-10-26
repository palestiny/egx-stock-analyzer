from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.subscriptions.model import Subscription, SubscriptionPlan, SubscriptionStatus


class SubscriptionStore(Protocol):
    def save_plan(self, plan: SubscriptionPlan) -> None: ...
    def get_plan(self, plan_id: str, version: int) -> SubscriptionPlan | None: ...
    def create(self, subscription: Subscription, *, actor: str, reason: str) -> None: ...
    def get(self, subscription_id: UUID) -> Subscription | None: ...
    def latest_for_user(self, user_id: UUID) -> Subscription | None: ...
    def transition(
        self,
        subscription_id: UUID,
        new_status: SubscriptionStatus,
        *,
        occurred_at,
        actor: str,
        reason: str,
    ) -> Subscription: ...
