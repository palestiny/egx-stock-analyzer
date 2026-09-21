from dataclasses import dataclass
from datetime import datetime

from app.application.analysis.automatic_analysis_retention import (
    AutomaticAnalysisRetention,
    AutomaticAnalysisRetentionResult,
    AutomaticRetentionPolicy,
)
from app.application.security.identity import AuthenticatedIdentity
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.persistence.sqlite_analysis_lifecycle_store import SQLiteAnalysisLifecycleStore


@dataclass(frozen=True)
class AutomaticRetentionCommandResult:
    status: str
    dry_run: bool
    purge: object | None

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
    try:
        capability = AutomaticAnalysisRetention(lifecycle_store, policy)
        result: AutomaticAnalysisRetentionResult = capability.execute(
            AuthenticatedIdentity.operator(),
            now=now,
            dry_run=dry_run,
        )
        status = "completed" if result.enabled else "disabled"
        return AutomaticRetentionCommandResult(
            status=status,
            dry_run=dry_run,
            purge=result.purge,
        )
    finally:
        lifecycle_store.close()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run bounded automatic analysis retention maintenance."
    )
    parser.add_argument(
        "--database",
        default="storage/analysis.db",
        help="SQLite database path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview eligible retention records without deleting them.",
    )
    args = parser.parse_args()

    from app.infrastructure.config import InfrastructureConfig

    config = InfrastructureConfig(
        analysis_database_path=args.database,
        automatic_retention_enabled=_environment_retention_enabled(),
        automatic_retention_days=_environment_retention_days(),
        automatic_retention_batch_limit=_environment_retention_batch_limit(),
    )
    result = run_automatic_retention(config, dry_run=args.dry_run)
    print(f"Retention status: {result.status}")
    print(f"Dry run: {result.dry_run}")
    print(f"Purged lifecycle units: {result.purged_lifecycle_units}")
    if result.operation_id is not None:
        print(f"Operation ID: {result.operation_id}")
    return 0


def _environment_retention_enabled() -> bool:
    from os import getenv

    from app.infrastructure.config import _parse_bool

    return _parse_bool(getenv("EGX_AUTOMATIC_RETENTION_ENABLED", "false"), "EGX_AUTOMATIC_RETENTION_ENABLED")


def _environment_retention_days() -> int:
    from os import getenv

    return int(getenv("EGX_AUTOMATIC_RETENTION_DAYS", "30"))


def _environment_retention_batch_limit() -> int:
    from os import getenv

    return int(getenv("EGX_AUTOMATIC_RETENTION_BATCH_LIMIT", "100"))


if __name__ == "__main__":
    raise SystemExit(main())