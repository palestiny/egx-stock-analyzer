from enum import Enum
from typing import Protocol
from uuid import UUID


class LifecycleDeletionOutcome(Enum):
    DELETED = "deleted"
    NOOP = "noop"
    ACTIVE = "active"


class AnalysisLifecycleStore(Protocol):
    def delete_run(
        self,
        run_id: UUID,
        actor_user_id: UUID,
        target_user_id: UUID | None,
    ) -> LifecycleDeletionOutcome:
        ...

    def delete_snapshot(
        self,
        snapshot_id: UUID,
        actor_user_id: UUID,
        target_user_id: UUID | None,
    ) -> LifecycleDeletionOutcome:
        ...

    def record_rejection(
        self,
        *,
        actor_user_id: UUID,
        action: str,
        target_user_id: UUID | None,
        outcome: str,
    ) -> None:
        ...

    def purge(
        self,
        *,
        actor_user_id: UUID,
        run_ids: tuple[UUID, ...] = (),
        snapshot_ids: tuple[UUID, ...] = (),
        limit: int = 100,
        dry_run: bool = False,
    ):
        ...
