import sqlite3
from datetime import datetime, timezone
from uuid import UUID


class ScheduledWorkflowExecutionHistoryQueries:
    def _connect(self) -> sqlite3.Connection:
        """Implemented by the concrete persistence store using the shared DB config."""
        raise NotImplementedError

    """SQLite query operations for scheduled-workflow transition history.

    The concrete store supplies the _connect() context-manager boundary.
    """

    def get_cross_execution_history(
        self,
        owner_user_id: UUID | None,
        global_only: bool,
        after_cursor: tuple[datetime, UUID, int] | None = None,
        limit: int | None = None,
        from_state: str | None = None,
        to_state: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> tuple[
        tuple[UUID, str, int, str | None, str, datetime, str | None], ...
    ]:
        query = """
            SELECT h.execution_id, e.occurrence_id, h.sequence,
                   h.from_state, h.to_state, h.occurred_at, h.reason
            FROM scheduled_workflow_execution_history AS h
            INNER JOIN scheduled_workflow_executions AS e
                ON e.execution_id = h.execution_id
            WHERE
                ((? = 1 AND e.owner_user_id IS NULL)
                 OR (? = 0 AND e.owner_user_id = ?))
        """
        parameters: list[object] = [
            1 if global_only else 0,
            1 if global_only else 0,
            str(owner_user_id) if owner_user_id is not None else None,
        ]

        if from_state is not None:
            query += " AND h.from_state = ?"
            parameters.append(from_state)

        if to_state is not None:
            query += " AND h.to_state = ?"
            parameters.append(to_state)

        if occurred_from is not None:
            query += " AND h.occurred_at >= ?"
            parameters.append(occurred_from.astimezone(timezone.utc).isoformat())

        if occurred_to is not None:
            query += " AND h.occurred_at < ?"
            parameters.append(occurred_to.astimezone(timezone.utc).isoformat())

        if after_cursor is not None:
            occurred_at, execution_id, sequence = after_cursor
            query += """
                AND (
                    h.occurred_at < ?
                    OR (
                        h.occurred_at = ?
                        AND (
                            h.execution_id < ?
                            OR (
                                h.execution_id = ?
                                AND h.sequence < ?
                            )
                        )
                    )
                )
            """
            parameters.extend(
                [
                    occurred_at.astimezone(timezone.utc).isoformat(),
                    occurred_at.astimezone(timezone.utc).isoformat(),
                    str(execution_id),
                    str(execution_id),
                    sequence,
                ]
            )

        query += """
            ORDER BY h.occurred_at DESC, h.execution_id DESC, h.sequence DESC
        """

        if limit is not None:
            query += " LIMIT ?"
            parameters.append(limit)

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        return tuple(
            (
                UUID(execution_id),
                occurrence_id,
                sequence,
                from_state,
                to_state,
                datetime.fromisoformat(occurred_at),
                reason,
            )
            for (
                execution_id,
                occurrence_id,
                sequence,
                from_state,
                to_state,
                occurred_at,
                reason,
            ) in rows
        )

    def get_history(
        self,
        execution_id: UUID,
        after_sequence: int | None = None,
        limit: int | None = None,
        from_state: str | None = None,
        to_state: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> tuple[tuple[int, str | None, str, datetime, str | None], ...]:
        query = """
            SELECT sequence, from_state, to_state, occurred_at, reason
            FROM scheduled_workflow_execution_history
            WHERE execution_id = ?
        """
        parameters: list[object] = [str(execution_id)]

        if from_state is not None:
            query += " AND from_state = ?"
            parameters.append(from_state)

        if to_state is not None:
            query += " AND to_state = ?"
            parameters.append(to_state)

        if occurred_from is not None:
            query += " AND occurred_at >= ?"
            parameters.append(occurred_from.astimezone(timezone.utc).isoformat())

        if occurred_to is not None:
            query += " AND occurred_at < ?"
            parameters.append(occurred_to.astimezone(timezone.utc).isoformat())

        if after_sequence is not None:
            query += " AND sequence > ?"
            parameters.append(after_sequence)

        query += " ORDER BY sequence ASC"

        if limit is not None:
            query += " LIMIT ?"
            parameters.append(limit)

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

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
