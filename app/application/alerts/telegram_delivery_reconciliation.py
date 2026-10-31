from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class TelegramDeliveryReconciliation:
    event_id: UUID
    user_id: UUID
    channel: str
    previous_status: str
    new_status: str
    outcome: str
    actor_subject: str
    reason: str
    occurred_at: datetime


class TelegramDeliveryReconciliationStore(Protocol):
    def list_unresolved(
        self, *, limit: int = 50, offset: int = 0
    ) -> tuple[dict[str, object], ...]: ...

    def reconcile(
        self,
        event_id: UUID,
        user_id: UUID,
        channel: str,
        *,
        outcome: str,
        actor_subject: str,
        reason: str,
        now: datetime,
    ) -> TelegramDeliveryReconciliation: ...

    def list_audit(
        self, *, limit: int = 50, offset: int = 0
    ) -> tuple[TelegramDeliveryReconciliation, ...]: ...
