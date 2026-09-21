import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.application.analysis.lifecycle_store import PurgeStoreResult


class SQLiteAnalysisLifecycleStore:
    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            for table, column in (
                ("analysis_runs", "deleted_at"),
                ("analysis_results", "deleted_at"),
            ):
                columns = {
                    row[1]
                    for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
                }
                if column not in columns:
                    connection.execute(
                        f"ALTER TABLE {table} ADD COLUMN {column} TEXT NULL"
                    )

    def delete_run(self, run_id: UUID, actor_user_id: UUID, target_user_id: UUID | None):
        from app.application.analysis.lifecycle_store import LifecycleDeletionOutcome

        occurred_at = datetime.now(timezone.utc).isoformat()
        audit_target = target_user_id or actor_user_id

        with self._connect() as connection:
            row = connection.execute(
                "SELECT state, deleted_at FROM analysis_runs WHERE run_id = ?",
                (str(run_id),),
            ).fetchone()
            if row is None:
                self._append_audit(
                    connection, actor_user_id, "analysis_run.delete", audit_target,
                    occurred_at, "not_found",
                )
                return LifecycleDeletionOutcome.NOOP

            if row[0] == "running" and row[1] is None:
                self._append_audit(
                    connection, actor_user_id, "analysis_run.delete", audit_target,
                    occurred_at, "rejected_active",
                )
                return LifecycleDeletionOutcome.ACTIVE

            if row[1] is not None:
                self._append_audit(
                    connection, actor_user_id, "analysis_run.delete", audit_target,
                    occurred_at, "noop",
                )
                return LifecycleDeletionOutcome.NOOP

            connection.execute(
                "UPDATE analysis_runs SET deleted_at = ? WHERE run_id = ? AND deleted_at IS NULL",
                (occurred_at, str(run_id)),
            )
            connection.execute(
                "UPDATE analysis_results SET deleted_at = ? WHERE analysis_run_id = ? AND deleted_at IS NULL",
                (occurred_at, str(run_id)),
            )
            self._append_audit(
                connection, actor_user_id, "analysis_run.delete", audit_target,
                occurred_at, "deleted",
            )
            return LifecycleDeletionOutcome.DELETED

    def delete_snapshot(self, snapshot_id: UUID, actor_user_id: UUID, target_user_id: UUID | None):
        from app.application.analysis.lifecycle_store import LifecycleDeletionOutcome

        occurred_at = datetime.now(timezone.utc).isoformat()
        audit_target = target_user_id or actor_user_id

        with self._connect() as connection:
            row = connection.execute(
                "SELECT deleted_at FROM analysis_results WHERE snapshot_id = ?",
                (str(snapshot_id),),
            ).fetchone()
            if row is None or row[0] is not None:
                self._append_audit(
                    connection, actor_user_id, "analysis_snapshot.delete", audit_target,
                    occurred_at, "noop",
                )
                return LifecycleDeletionOutcome.NOOP

            updated = connection.execute(
                """
                UPDATE analysis_results
                SET deleted_at = ?
                WHERE snapshot_id = ?
                  AND deleted_at IS NULL
                  AND NOT EXISTS (
                      SELECT 1
                      FROM analysis_runs
                      WHERE analysis_runs.run_id = analysis_results.analysis_run_id
                        AND analysis_runs.state = 'running'
                        AND analysis_runs.deleted_at IS NULL
                  )
                """,
                (occurred_at, str(snapshot_id)),
            )
            if updated.rowcount == 0:
                self._append_audit(
                    connection, actor_user_id, "analysis_snapshot.delete", audit_target,
                    occurred_at, "rejected_active",
                )
                return LifecycleDeletionOutcome.ACTIVE

            self._append_audit(
                connection, actor_user_id, "analysis_snapshot.delete", audit_target,
                occurred_at, "deleted",
            )
            return LifecycleDeletionOutcome.DELETED

    def find_retention_candidates(
        self,
        *,
        deleted_before: datetime,
        limit: int,
    ) -> list[tuple[str, UUID]]:
        if limit <= 0:
            raise ValueError("Retention batch limit must be positive")

        cutoff = deleted_before.astimezone(timezone.utc).isoformat()
        with self._connect() as connection:
            run_rows = connection.execute(
                """
                SELECT run_id
                FROM analysis_runs
                WHERE deleted_at IS NOT NULL
                  AND deleted_at <= ?
                  AND state != 'running'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM analysis_results
                      WHERE analysis_results.analysis_run_id = analysis_runs.run_id
                        AND (
                            analysis_results.deleted_at IS NULL
                            OR analysis_results.deleted_at > ?
                        )
                  )
                """,
                (cutoff, cutoff),
            ).fetchall()
            snapshot_rows = connection.execute(
                """
                SELECT snapshot_id
                FROM analysis_results
                WHERE deleted_at IS NOT NULL
                  AND deleted_at <= ?
                  AND analysis_run_id IS NULL
                """,
                (cutoff,),
            ).fetchall()

        candidates = [
            ("run", UUID(row[0]))
            for row in run_rows
        ] + [
            ("snapshot", UUID(row[0]))
            for row in snapshot_rows
        ]
        candidates.sort(key=lambda candidate: str(candidate[1]))
        return candidates[:limit]

    def purge(
        self,
        *,
        actor_user_id: UUID,
        run_ids: tuple[UUID, ...] = (),
        snapshot_ids: tuple[UUID, ...] = (),
        limit: int = 100,
        dry_run: bool = False,
        operation_id: UUID | None = None,
    ) -> PurgeStoreResult:
        if limit <= 0:
            raise ValueError("Purge limit must be positive")

        operation_id = operation_id or uuid4()
        selected_runs = list(dict.fromkeys(run_ids))
        selected_snapshots = list(dict.fromkeys(snapshot_ids))

        if len(selected_runs) + len(selected_snapshots) > limit:
            raise ValueError("Explicit purge selection exceeds the batch limit")

        if selected_runs or selected_snapshots:
            candidates = self._resolve_explicit_purge_candidates(
                selected_runs,
                selected_snapshots,
                limit,
            )
        else:
            candidates = self._find_eligible_purge_candidates(limit)

        if dry_run:
            with self._connect() as connection:
                self._append_audit(
                    connection,
                    actor_user_id,
                    f"analysis_lifecycle.purge:{operation_id}",
                    actor_user_id,
                    datetime.now(timezone.utc).isoformat(),
                    "dry_run",
                )
            return PurgeStoreResult(
                eligible_run_ids=tuple(
                    resource_id for kind, resource_id in candidates if kind == "run"
                ),
                eligible_snapshot_ids=tuple(
                    resource_id for kind, resource_id in candidates if kind == "snapshot"
                ),
                blocked_resource_ids=tuple(
                    resource_id for kind, resource_id in candidates if kind == "blocked"
                ),
            )

        purged_runs: list[UUID] = []
        purged_snapshots: list[UUID] = []
        blocked: list[UUID] = []

        for kind, resource_id in candidates:
            if kind == "blocked":
                blocked.append(resource_id)
                continue

            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                if kind == "run":
                    snapshot_count = self._purge_run_unit(
                        connection,
                        resource_id,
                        actor_user_id,
                        operation_id,
                    )
                    if snapshot_count is None:
                        blocked.append(resource_id)
                        connection.rollback()
                        continue
                    purged_runs.append(resource_id)
                else:
                    if not self._purge_snapshot_unit(
                        connection,
                        resource_id,
                        actor_user_id,
                        operation_id,
                    ):
                        blocked.append(resource_id)
                        connection.rollback()
                        continue
                    purged_snapshots.append(resource_id)

                connection.commit()
            except Exception as error:
                connection.rollback()
                self._append_audit(
                    connection,
                    actor_user_id,
                    f"analysis_lifecycle.purge:{operation_id}",
                    actor_user_id,
                    datetime.now(timezone.utc).isoformat(),
                    "failed",
                )
                connection.commit()
                connection.close()
                return PurgeStoreResult(
                    purged_run_ids=tuple(purged_runs),
                    purged_snapshot_ids=tuple(purged_snapshots),
                    blocked_resource_ids=tuple(blocked),
                    failure_resource_id=resource_id,
                    failure_reason=type(error).__name__,
                )
            finally:
                connection.close()

        with self._connect() as connection:
            outcome = (
                "dry_run"
                if dry_run
                else f"completed:runs={len(purged_runs)}:snapshots={len(purged_snapshots)}:blocked={len(blocked)}"
            )
            self._append_audit(
                connection,
                actor_user_id,
                f"analysis_lifecycle.purge:{operation_id}",
                actor_user_id,
                datetime.now(timezone.utc).isoformat(),
                outcome,
            )

        return PurgeStoreResult(
            purged_run_ids=tuple(purged_runs),
            purged_snapshot_ids=tuple(purged_snapshots),
            blocked_resource_ids=tuple(blocked),
        )

    def _find_eligible_purge_candidates(
        self,
        limit: int,
    ) -> list[tuple[str, UUID]]:
        with self._connect() as connection:
            run_rows = connection.execute(
                """
                SELECT run_id
                FROM analysis_runs
                WHERE deleted_at IS NOT NULL
                  AND state != 'running'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM analysis_results
                      WHERE analysis_results.analysis_run_id = analysis_runs.run_id
                        AND analysis_results.deleted_at IS NULL
                  )
                """,
            ).fetchall()
            snapshot_rows = connection.execute(
                """
                SELECT snapshot_id
                FROM analysis_results
                WHERE deleted_at IS NOT NULL
                  AND analysis_run_id IS NULL
                """,
            ).fetchall()

        candidates = [
            ("run", UUID(row[0]))
            for row in run_rows
        ] + [
            ("snapshot", UUID(row[0]))
            for row in snapshot_rows
        ]
        candidates.sort(key=lambda candidate: str(candidate[1]))
        return candidates[:limit]

    def _resolve_explicit_purge_candidates(
        self,
        run_ids: list[UUID],
        snapshot_ids: list[UUID],
        limit: int,
    ) -> list[tuple[str, UUID]]:
        resolved_runs: set[UUID] = set(run_ids)
        resolved_snapshots: set[UUID] = set()

        with self._connect() as connection:
            for snapshot_id in snapshot_ids:
                row = connection.execute(
                    "SELECT analysis_run_id FROM analysis_results WHERE snapshot_id = ?",
                    (str(snapshot_id),),
                ).fetchone()
                if row is None:
                    resolved_snapshots.add(snapshot_id)
                elif row[0] is None:
                    resolved_snapshots.add(snapshot_id)
                else:
                    resolved_runs.add(UUID(row[0]))

        candidates = [("run", run_id) for run_id in sorted(resolved_runs, key=str)]
        candidates.extend(
            ("snapshot", snapshot_id)
            for snapshot_id in sorted(resolved_snapshots, key=str)
            if len(candidates) < limit
        )
        return candidates

    def _purge_run_unit(
        self,
        connection: sqlite3.Connection,
        run_id: UUID,
        actor_user_id: UUID,
        operation_id: UUID,
    ) -> int | None:
        row = connection.execute(
            "SELECT state, deleted_at FROM analysis_runs WHERE run_id = ?",
            (str(run_id),),
        ).fetchone()
        if row is None or row[1] is None or row[0] == "running":
            return None

        non_deleted_snapshots = connection.execute(
            """
            SELECT snapshot_id
            FROM analysis_results
            WHERE analysis_run_id = ?
              AND deleted_at IS NULL
            """,
            (str(run_id),),
        ).fetchall()
        if non_deleted_snapshots:
            return None

        outcome_count = connection.execute(
            "SELECT COUNT(*) FROM analysis_run_outcomes WHERE run_id = ?",
            (str(run_id),),
        ).fetchone()[0]
        snapshot_count = connection.execute(
            "SELECT COUNT(*) FROM analysis_results WHERE analysis_run_id = ?",
            (str(run_id),),
        ).fetchone()[0]

        connection.execute(
            "DELETE FROM analysis_results WHERE analysis_run_id = ?",
            (str(run_id),),
        )
        connection.execute(
            "DELETE FROM analysis_run_outcomes WHERE run_id = ?",
            (str(run_id),),
        )
        deleted_run = connection.execute(
            "DELETE FROM analysis_runs WHERE run_id = ? AND deleted_at IS NOT NULL",
            (str(run_id),),
        )
        if deleted_run.rowcount != 1:
            return None

        self._append_audit(
            connection,
            actor_user_id,
            f"analysis_lifecycle.purge:{operation_id}",
            actor_user_id,
            datetime.now(timezone.utc).isoformat(),
            f"purged_run:snapshots={snapshot_count}:outcomes={outcome_count}",
        )
        return snapshot_count

    def _purge_snapshot_unit(
        self,
        connection: sqlite3.Connection,
        snapshot_id: UUID,
        actor_user_id: UUID,
        operation_id: UUID,
    ) -> bool:
        row = connection.execute(
            """
            SELECT analysis_run_id, deleted_at
            FROM analysis_results
            WHERE snapshot_id = ?
            """,
            (str(snapshot_id),),
        ).fetchone()
        if row is None or row[1] is None:
            return False
        if row[0] is not None:
            return False

        deleted_snapshot = connection.execute(
            "DELETE FROM analysis_results WHERE snapshot_id = ? AND deleted_at IS NOT NULL",
            (str(snapshot_id),),
        )
        if deleted_snapshot.rowcount != 1:
            return False

        self._append_audit(
            connection,
            actor_user_id,
            f"analysis_lifecycle.purge:{operation_id}",
            actor_user_id,
            datetime.now(timezone.utc).isoformat(),
            "purged_snapshot",
        )
        return True

    def record_rejection(
        self,
        *,
        actor_user_id: UUID,
        action: str,
        target_user_id: UUID | None,
        outcome: str,
    ) -> None:
        occurred_at = datetime.now(timezone.utc).isoformat()
        audit_target = target_user_id or actor_user_id
        with self._connect() as connection:
            self._append_audit(
                connection,
                actor_user_id,
                action,
                audit_target,
                occurred_at,
                outcome,
            )

    @staticmethod
    def _append_audit(
        connection: sqlite3.Connection,
        actor_user_id: UUID,
        action: str,
        target_user_id: UUID,
        occurred_at: str,
        outcome: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO management_audit
                (actor_user_id, action, target_user_id, occurred_at, outcome)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(actor_user_id),
                action,
                str(target_user_id),
                occurred_at,
                outcome,
            ),
        )
