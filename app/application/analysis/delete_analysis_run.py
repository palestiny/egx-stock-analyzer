from dataclasses import dataclass
from uuid import UUID

from app.application.analysis.lifecycle_store import (
    AnalysisLifecycleStore,
    LifecycleDeletionOutcome,
)
from app.application.analysis.run_store import AnalysisRunStore
from app.application.security.authorization import AuthorizationError, OwnershipAuthorizer
from app.application.security.identity import AuthenticatedIdentity
from app.domain.execution import ExecutionState


class AnalysisLifecycleNotFoundError(LookupError):
    """Raised when a lifecycle-managed resource does not exist."""


@dataclass(frozen=True)
class AnalysisLifecycleResult:
    deleted: bool


class DeleteAnalysisRun:
    def __init__(self, run_store: AnalysisRunStore, lifecycle_store: AnalysisLifecycleStore) -> None:
        self._run_store = run_store
        self._lifecycle_store = lifecycle_store
        self._authorizer = OwnershipAuthorizer()

    def execute(self, run_id: UUID, identity: AuthenticatedIdentity) -> AnalysisLifecycleResult:
        if identity.user_id is None:
            raise AuthorizationError("Authenticated user identity is required")

        run = self._run_store.get(run_id)
        if run is None:
            self._lifecycle_store.record_rejection(
                actor_user_id=identity.user_id,
                action="analysis_run.delete",
                target_user_id=None,
                outcome="not_found",
            )
            raise AnalysisLifecycleNotFoundError(f"Analysis run not found: {run_id}")

        try:
            self._authorizer.require_owner_or_operator(identity, run.owner_user_id)
        except AuthorizationError as error:
            self._lifecycle_store.record_rejection(
                actor_user_id=identity.user_id,
                action="analysis_run.delete",
                target_user_id=run.owner_user_id,
                outcome="forbidden",
            )
            raise AnalysisLifecycleNotFoundError(f"Analysis run not found: {run_id}") from error

        outcome = self._lifecycle_store.delete_run(
            run_id,
            identity.user_id,
            run.owner_user_id,
        )
        if outcome is LifecycleDeletionOutcome.ACTIVE:
            raise ValueError("Active analysis runs cannot be deleted")
        return AnalysisLifecycleResult(deleted=outcome is LifecycleDeletionOutcome.DELETED)
