import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionState,
    ScheduledWorkflowExecutionStore,
    ScheduledWorkflowExecutionIdempotencyConflictError,
)


class ScheduledWorkflowExecutionConflictError(ValueError):
    """Raised when a stale execution revision attempts to overwrite newer state."""


class SQLiteScheduledWorkflowExecutionStore(ScheduledWorkflowExecutionStore):
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = str(database_path)
        if self._database_path != ":memory:":
            Path(self._database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_workflow_executions (
                    execution_id TEXT PRIMARY KEY,
                    occurrence_id TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    analysis_state TEXT NULL,
                    delivery_state TEXT NULL,
                    owner_user_id TEXT NULL,
                    request_fingerprint TEXT NULL,
                    revision INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(scheduled_workflow_executions)"
                ).fetchall()
            }
            if "owner_user_id" not in columns:
                connection.execute(
                    "ALTER TABLE scheduled_workflow_executions "
                    "ADD COLUMN owner_user_id TEXT NULL"
                )
            if "request_fingerprint" not in columns:
                connection.execute(
                    "ALTER TABLE scheduled_workflow_executions "
                    "ADD COLUMN request_fingerprint TEXT NULL"
                )
            if "revision" not in columns:
                connection.execute(
                    "ALTER TABLE scheduled_workflow_executions "
                    "ADD COLUMN revision INTEGER NOT NULL DEFAULT 0"
                )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_workflow_execution_history (
                    execution_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    from_state TEXT NULL,
                    to_state TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    reason TEXT NULL,
                    PRIMARY KEY (execution_id, sequence),
                    FOREIGN KEY (execution_id)
                        REFERENCES scheduled_workflow_executions(execution_id)
                )
                """
            )
            history_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(scheduled_workflow_execution_history)"
                ).fetchall()
            }
            if "reason" not in history_columns:
                connection.execute(
                    "ALTER TABLE scheduled_workflow_execution_history "
                    "ADD COLUMN reason TEXT NULL"
                )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_scheduled_workflow_executions_state
                ON scheduled_workflow_executions (state)
                """
            )

    def create_or_get(
        self,
        occurrence_id: str,
        now: datetime,
        owner_user_id: UUID | None = None,
        request_fingerprint: str | None = None,
    ) -> ScheduledWorkflowExecution:
        normalized = occurrence_id.strip()
        if not normalized:
            raise ValueError("occurrence_id cannot be empty")

        fingerprint = request_fingerprint
        with self._connect() as connection:
            execution = ScheduledWorkflowExecution.create(
                normalized,
                now,
                owner_user_id=owner_user_id,
                request_fingerprint=fingerprint,
            )
            cursor = connection.execute(
                """
                INSERT INTO scheduled_workflow_executions (
                    execution_id,
                    occurrence_id,
                    state,
                    created_at,
                    updated_at,
                    analysis_state,
                    delivery_state,
                    owner_user_id,
                    request_fingerprint,
                    revision
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(occurrence_id) DO NOTHING
                """,
                (
                    str(execution.id),
                    execution.occurrence_id,
                    execution.state.value,
                    execution.created_at.isoformat(),
                    execution.updated_at.isoformat(),
                    execution.analysis_state,
                    execution.delivery_state,
                    str(execution.owner_user_id)
                    if execution.owner_user_id is not None
                    else None,
                    execution.request_fingerprint,
                    execution.revision,
                ),
            )

            if cursor.rowcount == 1:
                self._insert_created_history(connection, execution)
                return execution

            row = connection.execute(
                """
                SELECT execution_id, occurrence_id, state, created_at,
                       updated_at, analysis_state, delivery_state,
                       owner_user_id, request_fingerprint, revision
                FROM scheduled_workflow_executions
                WHERE occurrence_id = ?
                """,
                (normalized,),
            ).fetchone()
            if row is None:
                raise RuntimeError(
                    "Scheduled workflow reservation conflict could not resolve "
                    f"occurrence: {normalized}"
                )

            existing = self._to_execution(row)
            if existing.request_fingerprint is None and fingerprint is not None:
                updated = connection.execute(
                    """
                    UPDATE scheduled_workflow_executions
                    SET request_fingerprint = ?
                    WHERE execution_id = ? AND revision = ? AND request_fingerprint IS NULL
                    """,
                    (
                        fingerprint,
                        str(existing.id),
                        existing.revision,
                    ),
                ).rowcount
                if updated == 1:
                    return ScheduledWorkflowExecution(
                        id=existing.id,
                        occurrence_id=existing.occurrence_id,
                        state=existing.state,
                        created_at=existing.created_at,
                        updated_at=existing.updated_at,
                        owner_user_id=existing.owner_user_id,
                        analysis_state=existing.analysis_state,
                        delivery_state=existing.delivery_state,
                        request_fingerprint=fingerprint,
                        revision=existing.revision,
                    )
                row = connection.execute(
                    """
                    SELECT execution_id, occurrence_id, state, created_at,
                           updated_at, analysis_state, delivery_state,
                           owner_user_id, request_fingerprint, revision
                    FROM scheduled_workflow_executions
                    WHERE occurrence_id = ?
                    """,
                    (normalized,),
                ).fetchone()
                if row is None:
                    raise RuntimeError(
                        "Scheduled workflow reservation conflict could not resolve "
                        f"occurrence: {normalized}"
                    )
                existing = self._to_execution(row)

            if (
                existing.request_fingerprint is not None
                and existing.request_fingerprint != fingerprint
            ):
                raise ScheduledWorkflowExecutionIdempotencyConflictError(
                    "Idempotency key is already bound to a different request: "
                    f"{normalized}"
                )
            return existing

    def start_if_created(
        self,
        execution_id: UUID,
        now: datetime,
    ) -> ScheduledWorkflowExecution | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT execution_id, occurrence_id, state, created_at,
                       updated_at, analysis_state, delivery_state,
                       owner_user_id, request_fingerprint, revision
                FROM scheduled_workflow_executions
                WHERE execution_id = ?
                """,
                (str(execution_id),),
            ).fetchone()
            if row is None:
                raise ValueError(
                    f"Unknown scheduled workflow execution: {execution_id}"
                )

            current = self._to_execution(row)
            if current.state is not ScheduledWorkflowExecutionState.CREATED:
                return None

            started = current.start(now)
            updated = connection.execute(
                """
                UPDATE scheduled_workflow_executions
                SET state = ?, updated_at = ?, revision = ?
                WHERE execution_id = ? AND state = ? AND revision = ?
                """,
                (
                    started.state.value,
                    started.updated_at.isoformat(),
                    started.revision,
                    str(started.id),
                    ScheduledWorkflowExecutionState.CREATED.value,
                    current.revision,
                ),
            ).rowcount
            if updated != 1:
                return None

            sequence = self._next_history_sequence(connection, started.id)
            connection.execute(
                """
                INSERT INTO scheduled_workflow_execution_history (
                    execution_id, sequence, from_state, to_state, occurred_at, reason
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(started.id),
                    sequence,
                    current.state.value,
                    started.state.value,
                    started.updated_at.isoformat(),
                    started.transition_reason,
                ),
            )
            return started

    def save(self, execution: ScheduledWorkflowExecution) -> None:
        with self._connect() as connection:
            current_row = connection.execute(
                """
                SELECT execution_id, occurrence_id, state, created_at,
                       updated_at, analysis_state, delivery_state,
                       owner_user_id, request_fingerprint, revision
                FROM scheduled_workflow_executions
                WHERE execution_id = ?
                """,
                (str(execution.id),),
            ).fetchone()
            if current_row is None:
                raise ValueError(
                    f"Unknown scheduled workflow execution: {execution.id}"
                )

            current = self._to_execution(current_row)
            if execution.revision == current.revision:
                if self._same_persisted_state(execution, current):
                    return
                raise ScheduledWorkflowExecutionConflictError(
                    f"Execution revision already exists: {execution.id}"
                )

            if execution.revision != current.revision + 1:
                raise ScheduledWorkflowExecutionConflictError(
                    f"Stale execution revision for {execution.id}: "
                    f"expected {current.revision + 1}, got {execution.revision}"
                )

            updated = connection.execute(
                """
                UPDATE scheduled_workflow_executions
                SET state = ?, updated_at = ?, analysis_state = ?,
                    delivery_state = ?, owner_user_id = ?,
                    request_fingerprint = ?, revision = ?
                WHERE execution_id = ? AND revision = ?
                """,
                (
                    execution.state.value,
                    execution.updated_at.isoformat(),
                    execution.analysis_state,
                    execution.delivery_state,
                    str(execution.owner_user_id)
                    if execution.owner_user_id is not None
                    else None,
                    execution.request_fingerprint,
                    execution.revision,
                    str(execution.id),
                    current.revision,
                ),
            ).rowcount

            if updated != 1:
                raise ScheduledWorkflowExecutionConflictError(
                    f"Execution revision changed while saving: {execution.id}"
                )

            if execution.state is not current.state:
                sequence = self._next_history_sequence(connection, execution.id)
                connection.execute(
                    """
                    INSERT INTO scheduled_workflow_execution_history (
                        execution_id, sequence, from_state, to_state, occurred_at, reason
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(execution.id),
                        sequence,
                        current.state.value,
                        execution.state.value,
                        execution.updated_at.isoformat(),
                        execution.transition_reason,
                    ),
                )

    def get_by_occurrence(
        self,
        occurrence_id: str,
    ) -> ScheduledWorkflowExecution | None:
        normalized = occurrence_id.strip()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT execution_id, occurrence_id, state, created_at,
                       updated_at, analysis_state, delivery_state,
                       owner_user_id, request_fingerprint, revision
                FROM scheduled_workflow_executions
                WHERE occurrence_id = ?
                """,
                (normalized,),
            ).fetchone()

        return self._to_execution(row) if row is not None else None

    def get(
        self,
        execution_id: UUID,
    ) -> ScheduledWorkflowExecution | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT execution_id, occurrence_id, state, created_at,
                       updated_at, analysis_state, delivery_state,
                       owner_user_id, request_fingerprint, revision
                FROM scheduled_workflow_executions
                WHERE execution_id = ?
                """,
                (str(execution_id),),
            ).fetchone()

        return self._to_execution(row) if row is not None else None

    def get_history(
        self,
        execution_id: UUID,
    ) -> tuple[tuple[int, str | None, str, datetime, str | None], ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT sequence, from_state, to_state, occurred_at, reason
                FROM scheduled_workflow_execution_history
                WHERE execution_id = ?
                ORDER BY sequence ASC
                """,
                (str(execution_id),),
            ).fetchall()

        return tuple(
            (
                sequence,
                from_state,
                to_state,
                datetime.fromisoformat(occurred_at),
                reason,
            )
            for sequence, from_state, to_state, occurred_at, reason in rows
        )

    def recover_running(
        self,
        now: datetime,
    ) -> tuple[ScheduledWorkflowExecution, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT execution_id, occurrence_id, state, created_at,
                       updated_at, analysis_state, delivery_state,
                       owner_user_id, request_fingerprint, revision
                FROM scheduled_workflow_executions
                WHERE state = ?
                ORDER BY created_at ASC, execution_id ASC
                """,
                (ScheduledWorkflowExecutionState.RUNNING.value,),
            ).fetchall()

        recovered = []
        for row in rows:
            execution = self._to_execution(row)
            interrupted = execution.interrupt(now, reason="startup recovery")
            self.save(interrupted)
            recovered.append(interrupted)

        return tuple(recovered)

    def list_all(
        self,
    ) -> tuple[ScheduledWorkflowExecution, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT execution_id, occurrence_id, state, created_at,
                       updated_at, analysis_state, delivery_state,
                       owner_user_id, request_fingerprint, revision
                FROM scheduled_workflow_executions
                ORDER BY created_at DESC, execution_id DESC
                """
            ).fetchall()

        return tuple(self._to_execution(row) for row in rows)

    def list_interrupted(
        self,
    ) -> tuple[ScheduledWorkflowExecution, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT execution_id, occurrence_id, state, created_at,
                       updated_at, analysis_state, delivery_state,
                       owner_user_id, request_fingerprint, revision
                FROM scheduled_workflow_executions
                WHERE state = ?
                ORDER BY occurrence_id ASC, execution_id ASC
                """,
                (ScheduledWorkflowExecutionState.INTERRUPTED.value,),
            ).fetchall()

        return tuple(self._to_execution(row) for row in rows)

    @staticmethod
    def _same_persisted_state(
        left: ScheduledWorkflowExecution,
        right: ScheduledWorkflowExecution,
    ) -> bool:
        return (
            left.id == right.id
            and left.occurrence_id == right.occurrence_id
            and left.state is right.state
            and left.created_at == right.created_at
            and left.updated_at == right.updated_at
            and left.owner_user_id == right.owner_user_id
            and left.analysis_state == right.analysis_state
            and left.delivery_state == right.delivery_state
            and left.request_fingerprint == right.request_fingerprint
            and left.revision == right.revision
        )

    @staticmethod
    def _insert_created_history(
        connection: sqlite3.Connection,
        execution: ScheduledWorkflowExecution,
    ) -> None:
        connection.execute(
            """
            INSERT INTO scheduled_workflow_execution_history (
                execution_id, sequence, from_state, to_state, occurred_at, reason
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(execution.id),
                1,
                None,
                execution.state.value,
                execution.created_at.isoformat(),
                execution.transition_reason,
            ),
        )

    @staticmethod
    def _next_history_sequence(
        connection: sqlite3.Connection,
        execution_id: UUID,
    ) -> int:
        row = connection.execute(
            """
            SELECT COALESCE(MAX(sequence), 0) + 1
            FROM scheduled_workflow_execution_history
            WHERE execution_id = ?
            """,
            (str(execution_id),),
        ).fetchone()
        return int(row[0])

    @staticmethod
    def _to_execution(
        row: tuple[
            str,
            str,
            str,
            str,
            str,
            str | None,
            str | None,
            str | None,
            str | None,
            int,
        ],
    ) -> ScheduledWorkflowExecution:
        (
            execution_id,
            occurrence_id,
            state,
            created_at,
            updated_at,
            analysis_state,
            delivery_state,
            owner_user_id,
            request_fingerprint,
            revision,
        ) = row
        return ScheduledWorkflowExecution(
            id=UUID(execution_id),
            occurrence_id=occurrence_id,
            state=ScheduledWorkflowExecutionState(state),
            created_at=datetime.fromisoformat(created_at),
            updated_at=datetime.fromisoformat(updated_at),
            analysis_state=analysis_state,
            delivery_state=delivery_state,
            owner_user_id=UUID(owner_user_id) if owner_user_id is not None else None,
            request_fingerprint=request_fingerprint,
            revision=revision,
        )
