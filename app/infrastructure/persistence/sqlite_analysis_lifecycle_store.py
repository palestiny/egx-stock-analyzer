import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID


class SQLiteAnalysisLifecycleStore:
    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)

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

            connection.execute(
                "UPDATE analysis_results SET deleted_at = ? WHERE snapshot_id = ? AND deleted_at IS NULL",
                (occurred_at, str(snapshot_id)),
            )
            self._append_audit(
                connection, actor_user_id, "analysis_snapshot.delete", audit_target,
                occurred_at, "deleted",
            )
            return LifecycleDeletionOutcome.DELETED

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
