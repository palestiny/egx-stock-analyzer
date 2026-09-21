from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.application.analysis.lifecycle_store import AnalysisLifecycleStore
from app.application.analysis.purge_analysis_lifecycle import (
    PurgeAnalysisLifecycle,
    PurgeAnalysisLifecycleResult,
)
from app.application.security.identity import AuthenticatedIdentity


@dataclass(frozen=True)
class AutomaticRetentionPolicy:
    enabled: bool = False
    preservation_days: int = 30
    batch_limit: int = 100

    def validate(self) -> None:
        if not isinstance(self.preservation_days, int) or isinstance(
            self.preservation_days, bool
        ):
            raise ValueError("Preservation days must be an integer")
        if self.preservation_days <= 0:
            raise ValueError("Preservation days must be positive")
        if not isinstance(self.batch_limit, int) or isinstance(self.batch_limit, bool):
            raise ValueError("Retention batch limit must be an integer")
        if self.batch_limit <= 0:
            raise ValueError("Retention batch limit must be positive")


@dataclass(frozen=True)
class AutomaticAnalysisRetentionResult:
    enabled: bool
    cutoff: datetime
    purge: PurgeAnalysisLifecycleResult | None

    @property
    def purged_run_ids(self) -> tuple[UUID, ...]:
        return () if self.purge is None else self.purge.purged_run_ids

    @property
    def purged_snapshot_ids(self) -> tuple[UUID, ...]:
        return () if self.purge is None else self.purge.purged_snapshot_ids


class AutomaticAnalysisRetention:
    OPERATION_NAME = "analysis_lifecycle.automatic_retention"

    def __init__(
        self,
        lifecycle_store: AnalysisLifecycleStore,
        policy: AutomaticRetentionPolicy | None = None,
    ) -> None:
        self._lifecycle_store = lifecycle_store
        self._purge = PurgeAnalysisLifecycle(lifecycle_store)
        self._policy = policy or AutomaticRetentionPolicy()

    def execute(
        self,
        identity: AuthenticatedIdentity,
        *,
        now: datetime | None = None,
        dry_run: bool = False,
    ) -> AutomaticAnalysisRetentionResult:
        policy = self._policy
        policy.validate()
        occurred_at = now or datetime.now(timezone.utc)
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError("Retention evaluation time must be timezone-aware")

        occurred_at = occurred_at.astimezone(timezone.utc)
        cutoff = occurred_at - timedelta(days=policy.preservation_days)

        if not policy.enabled:
            return AutomaticAnalysisRetentionResult(
                enabled=False,
                cutoff=cutoff,
                purge=None,
            )

        candidates = self._lifecycle_store.find_retention_candidates(
            deleted_before=cutoff,
            limit=policy.batch_limit,
        )
        run_ids = tuple(
            resource_id for kind, resource_id in candidates if kind == "run"
        )
        snapshot_ids = tuple(
            resource_id for kind, resource_id in candidates if kind == "snapshot"
        )

        purge_result = self._purge.execute(
            identity,
            run_ids=run_ids,
            snapshot_ids=snapshot_ids,
            limit=policy.batch_limit,
            dry_run=dry_run,
            operation_name=self.OPERATION_NAME,
        )
        return AutomaticAnalysisRetentionResult(
            enabled=True,
            cutoff=cutoff,
            purge=purge_result,
        )
