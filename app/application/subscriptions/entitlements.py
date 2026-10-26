from typing import Protocol
from uuid import UUID

from app.domain.subscriptions.entitlement import EntitlementGrant


class EntitlementStore(Protocol):
    def grant(self, grant: EntitlementGrant) -> EntitlementGrant: ...
    def revoke(
        self,
        grant_id: UUID,
        *,
        revoked_at,
        revoked_by: UUID,
        reason: str,
    ) -> EntitlementGrant | None: ...
    def get(self, grant_id: UUID) -> EntitlementGrant | None: ...
    def for_user(self, user_id: UUID) -> tuple[EntitlementGrant, ...]: ...


class EntitlementService:
    """Central capability evaluator shared by API and messaging authorization."""

    def __init__(self, store: EntitlementStore) -> None:
        self._store = store

    def allows(self, user_id: UUID, capability: str, *, at) -> bool:
        normalized = capability.strip()
        if not normalized:
            raise ValueError("capability is required")
        return any(
            grant.capability == normalized and grant.active_at(at)
            for grant in self._store.for_user(user_id)
        )

    def require(self, user_id: UUID, capability: str, *, at) -> None:
        if not self.allows(user_id, capability, at=at):
            raise PermissionError(f"entitlement required: {capability}")
