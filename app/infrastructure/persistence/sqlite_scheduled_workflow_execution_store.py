import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionState,
    ScheduledWorkflowExecutionStore,
)


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
                    updated_at TEXT NOT NULL
                )
                """
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
    ) -> ScheduledWorkflowExecution:
        normalized = occurrence_id.strip()
        if not normalized:
            raise ValueError("occurrence_id cannot be empty")

        existing = self.get_by_occurrence(normalized)
        if existing is not None:
            return existing

        execution = ScheduledWorkflowExecution.create(normalized, now)

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO scheduled_workflow_executions (
                    execution_id,
                    occurrence_id,
                    state,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(execution.id),
                    execution.occurrence_id,
                    execution.state.value,
                    execution.created_at.isoformat(),
                    execution.updated_at.isoformat(),
                ),
            )

        return execution

    def save(self, execution: ScheduledWorkflowExecution) -> None:
        with self._connect() as connection:
            updated = connection.execute(
                """
                UPDATE scheduled_workflow_executions
                SET state = ?, updated_at = ?
                WHERE execution_id = ?
                """,
                (
                    execution.state.value,
                    execution.updated_at.isoformat(),
                    str(execution.id),
                ),
            ).rowcount

        if updated != 1:
            raise ValueError(
                f"Unknown scheduled workflow execution: {execution.id}"
            )

    def get_by_occurrence(
        self,
        occurrence_id: str,
    ) -> ScheduledWorkflowExecution | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT execution_id, occurrence_id, state, created_at, updated_at
                FROM scheduled_workflow_executions
                WHERE occurrence_id = ?
                """,
                (occurrence_id.strip(),),
            ).fetchone()

        return self._to_execution(row) if row is not None else None

    def get(self, execution_id: UUID) -> ScheduledWorkflowExecution | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT execution_id, occurrence_id, state, created_at, updated_at
                FROM scheduled_workflow_executions
                WHERE execution_id = ?
                """,
                (str(execution_id),),
            ).fetchone()

        return self._to_execution(row) if row is not None else None

    def recover_running(
        self,
        now: datetime,
    ) -> tuple[ScheduledWorkflowExecution, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT execution_id, occurrence_id, state, created_at, updated_at
                FROM scheduled_workflow_executions
                WHERE state = ?
                ORDER BY created_at ASC, execution_id ASC
                """,
                (ScheduledWorkflowExecutionState.RUNNING.value,),
            ).fetchall()

        recovered = []
        for row in rows:
            execution = self._to_execution(row)
            interrupted = execution.interrupt(now)
            self.save(interrupted)
            recovered.append(interrupted)

        return tuple(recovered)

    @staticmethod
    def _to_execution(
        row: tuple[str, str, str, str, str],
    ) -> ScheduledWorkflowExecution:
        execution_id, occurrence_id, state, created_at, updated_at = row
        return ScheduledWorkflowExecution(
            id=UUID(execution_id),
            occurrence_id=occurrence_id,
            state=ScheduledWorkflowExecutionState(state),
            created_at=datetime.fromisoformat(created_at),
            updated_at=datetime.fromisoformat(updated_at),
        )
