from dataclasses import dataclass, replace
from datetime import datetime

from app.application.analysis.automatic_analysis_retention import (
    AutomaticAnalysisRetention,
    AutomaticAnalysisRetentionResult,
    AutomaticRetentionPolicy,
)
from app.application.analysis.purge_analysis_lifecycle import PurgeAnalysisLifecycleResult
from app.application.security.identity import AuthenticatedIdentity
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.persistence.sqlite_analysis_lifecycle_store import SQLiteAnalysisLifecycleStore


@dataclass(frozen=True)
class AutomaticRetentionCommandResult:
    status: str
    dry_run: bool
    purge: PurgeAnalysisLifecycleResult | None

    @property
    def exit_code(self) -> int:
        return 1 if self.status == "failed" else 0

    @property
    def purged_lifecycle_units(self) -> int:
        if self.purge is None:
            return 0
        return len(self.purge.purged_run_ids) + len(self.purge.purged_snapshot_ids)

    @property
    def operation_id(self):
        return None if self.purge is None else self.purge.operation_id


def run_automatic_retention(
    config: InfrastructureConfig,
    *,
    dry_run: bool = False,
    now: datetime | None = None,
) -> AutomaticRetentionCommandResult:
    policy = AutomaticRetentionPolicy(
        enabled=config.automatic_retention_enabled,
        preservation_days=config.automatic_retention_days,
        batch_limit=config.automatic_retention_batch_limit,
    )
    lifecycle_store = SQLiteAnalysisLifecycleStore(config.analysis_database_path)
    capability = AutomaticAnalysisRetention(lifecycle_store, policy)
    result: AutomaticAnalysisRetentionResult = capability.execute(
        AuthenticatedIdentity.operator(),
        now=now,
        dry_run=dry_run,
    )
    status = "disabled" if not result.enabled else "completed"
    if result.purge is not None and result.purge.failure_reason is not None:
        status = "failed"
    return AutomaticRetentionCommandResult(
        status=status,
        dry_run=dry_run,
        purge=result.purge,
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run bounded automatic analysis retention maintenance."
    )
    parser.add_argument(
        "--database",
        default=None,
        help="Optional SQLite database path override.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview eligible retention records without deleting them.",
    )
    args = parser.parse_args()

    try:
        config = InfrastructureConfig.from_environment()
        if args.database is not None:
            config = replace(config, analysis_database_path=args.database)

        result = run_automatic_retention(config, dry_run=args.dry_run)
    except Exception as error:
        print(f"Retention status: failed ({type(error).__name__})")
        print(f"Retention error: {error}")
        return 1

    print(f"Retention status: {result.status}")
    print(f"Dry run: {result.dry_run}")
    print(f"Purged lifecycle units: {result.purged_lifecycle_units}")
    if result.operation_id is not None:
        print(f"Operation ID: {result.operation_id}")
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())