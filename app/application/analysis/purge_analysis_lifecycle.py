from dataclasses import dataclass
from uuid import UUID, uuid4

from app.application.analysis.lifecycle_store import AnalysisLifecycleStore
from app.application.security.authorization import AuthorizationError, OperatorAuthorizer
from app.application.security.identity import AuthenticatedIdentity, Permission


@dataclass(frozen=True)
class PurgeAnalysisLifecycleResult:
    operation_id: UUID
    dry_run: bool
    purged_run_ids: tuple[UUID, ...]
    purged_snapshot_ids: tuple[UUID, ...]
    eligible_run_ids: tuple[UUID, ...] = ()
    eligible_snapshot_ids: tuple[UUID, ...] = ()
    blocked_resource_ids: tuple[UUID, ...] = ()
    failure_resource_id: UUID | None = None
    failure_reason: str | None = None

    @property
    def purged_lifecycle_units(self) -> int:
        return len(self.purged_run_ids) + len(
            [snapshot_id for snapshot_id in self.purged_snapshot_ids]
        )


class PurgeAnalysisLifecycle:
    def __init__(self, lifecycle_store: AnalysisLifecycleStore) -> None:
        self._lifecycle_store = lifecycle_store
        self._operator_authorizer = OperatorAuthorizer()

    def execute(
        self,
        identity: AuthenticatedIdentity,
        *,
        run_ids: tuple[UUID, ...] = (),
        snapshot_ids: tuple[UUID, ...] = (),
        limit: int = 100,
        dry_run: bool = False,
    ) -> PurgeAnalysisLifecycleResult:
        self._operator_authorizer.require(identity, Permission.OPERATOR)
        if identity.user_id is None:
            raise AuthorizationError("Authenticated operator identity is required")
        if limit <= 0:
            raise ValueError("Purge limit must be positive")
        if len(run_ids) + len(snapshot_ids) > limit:
            raise ValueError("Explicit purge selection exceeds the batch limit")

        operation_id = uuid4()
        result = self._lifecycle_store.purge(
            actor_user_id=identity.user_id,
            run_ids=run_ids,
            snapshot_ids=snapshot_ids,
            limit=limit,
            dry_run=dry_run,
        )
        return PurgeAnalysisLifecycleResult(
            operation_id=operation_id,
            dry_run=dry_run,
            purged_run_ids=tuple(result.purged_run_ids),
            purged_snapshot_ids=tuple(result.purged_snapshot_ids),
            eligible_run_ids=tuple(result.eligible_run_ids),
            eligible_snapshot_ids=tuple(result.eligible_snapshot_ids),
            blocked_resource_ids=tuple(result.blocked_resource_ids),
            failure_resource_id=result.failure_resource_id,
            failure_reason=result.failure_reason,
        )
