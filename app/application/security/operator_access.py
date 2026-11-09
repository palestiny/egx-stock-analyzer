from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.application.security.identity import AuthenticatedIdentity, Permission


@dataclass(frozen=True)
class OperatorAccessEvent:
    event_id: int
    action: str
    target_user_id: UUID
    actor_user_id: UUID | None
    actor_credential_id: UUID | None
    actor_kind: str
    reason: str
    occurred_at: datetime


class OperatorAccessStore(Protocol):
    def is_operator(self, user_id: UUID) -> bool:
        ...

    def grant(
        self,
        target_user_id: UUID,
        *,
        actor_user_id: UUID,
        actor_credential_id: UUID,
        reason: str,
    ) -> None:
        ...

    def revoke(
        self,
        target_user_id: UUID,
        *,
        actor_user_id: UUID,
        actor_credential_id: UUID,
        reason: str,
    ) -> None:
        ...

    def bootstrap_first_operator(self, target_user_id: UUID, *, reason: str) -> None:
        ...

    def list_events(self) -> tuple[OperatorAccessEvent, ...]:
        ...


class OperatorAccessError(ValueError):
    pass


class OperatorAccessService:
    def __init__(self, store: OperatorAccessStore) -> None:
        self._store = store

    def grant(self, actor: AuthenticatedIdentity, target_user_id: UUID, reason: str) -> None:
        self._require_individual_operator(actor)
        normalized_reason = self._normalize_reason(reason)
        assert actor.user_id is not None and actor.credential_id is not None
        try:
            self._store.grant(
                target_user_id,
                actor_user_id=actor.user_id,
                actor_credential_id=actor.credential_id,
                reason=normalized_reason,
            )
        except (ValueError, KeyError) as error:
            raise OperatorAccessError(str(error)) from error

    def list_events(self, actor: AuthenticatedIdentity) -> tuple[OperatorAccessEvent, ...]:
        self._require_individual_operator(actor)
        return self._store.list_events()

    def revoke(self, actor: AuthenticatedIdentity, target_user_id: UUID, reason: str) -> None:
        self._require_individual_operator(actor)
        normalized_reason = self._normalize_reason(reason)
        assert actor.user_id is not None and actor.credential_id is not None
        try:
            self._store.revoke(
                target_user_id,
                actor_user_id=actor.user_id,
                actor_credential_id=actor.credential_id,
                reason=normalized_reason,
            )
        except (ValueError, KeyError) as error:
            raise OperatorAccessError(str(error)) from error

    @staticmethod
    def _require_individual_operator(actor: AuthenticatedIdentity) -> None:
        if (
            Permission.OPERATOR not in actor.permissions
            or actor.user_id is None
            or actor.credential_id is None
        ):
            raise OperatorAccessError("An individually authenticated operator credential is required")

    @staticmethod
    def _normalize_reason(reason: str) -> str:
        normalized = reason.strip()
        if not normalized or len(normalized) > 500:
            raise OperatorAccessError("A reason between 1 and 500 characters is required")
        return normalized
