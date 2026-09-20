from dataclasses import dataclass
from uuid import UUID

from app.application.analysis.lifecycle_store import (
    AnalysisLifecycleStore,
    LifecycleDeletionOutcome,
)
from app.application.analysis.result_store import AnalysisResultStore
from app.application.security.authorization import AuthorizationError, OwnershipAuthorizer
from app.application.security.identity import AuthenticatedIdentity


@dataclass(frozen=True)
class AnalysisSnapshotLifecycleResult:
    deleted: bool


class DeleteAnalysisSnapshot:
    def __init__(
        self,
        result_store: AnalysisResultStore,
        lifecycle_store: AnalysisLifecycleStore,
    ) -> None:
        self._result_store = result_store
        self._lifecycle_store = lifecycle_store
        self._authorizer = OwnershipAuthorizer()

    def execute(
        self,
        snapshot_id: UUID,
        identity: AuthenticatedIdentity,
    ) -> AnalysisSnapshotLifecycleResult:
        if identity.user_id is None:
            raise AuthorizationError("Authenticated user identity is required")

        record = self._result_store.get_snapshot(snapshot_id)
        if record is None:
            self._lifecycle_store.record_rejection(
                actor_user_id=identity.user_id,
                action="analysis_snapshot.delete",
                target_user_id=None,
                outcome="not_found",
            )
            return AnalysisSnapshotLifecycleResult(deleted=False)

        try:
            self._authorizer.require_owner_or_operator(identity, record.owner_user_id)
        except AuthorizationError as error:
            self._lifecycle_store.record_rejection(
                actor_user_id=identity.user_id,
                action="analysis_snapshot.delete",
                target_user_id=record.owner_user_id,
                outcome="forbidden",
            )
            return AnalysisSnapshotLifecycleResult(deleted=False)

        outcome = self._lifecycle_store.delete_snapshot(
            snapshot_id,
            identity.user_id,
            record.owner_user_id,
        )
        return AnalysisSnapshotLifecycleResult(
            deleted=outcome is LifecycleDeletionOutcome.DELETED,
        )
