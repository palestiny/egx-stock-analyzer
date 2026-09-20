import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.application.analysis.run_store import AnalysisRunStore
from app.domain.analysis_run import (
    AnalysisRun,
    AnalysisRunOutcome,
    AnalysisRunOutcomeState,
)
from app.domain.execution import ExecutionState


class SQLiteAnalysisRunStore(AnalysisRunStore):
    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    state TEXT NOT NULL,
                    owner_user_id TEXT NULL,
                    outcomes_available INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(analysis_runs)"
                ).fetchall()
            }
            if "owner_user_id" not in columns:
                connection.execute(
                    "ALTER TABLE analysis_runs ADD COLUMN owner_user_id TEXT NULL"
                )
            if "outcomes_available" not in columns:
                connection.execute(
                    "ALTER TABLE analysis_runs ADD COLUMN outcomes_available INTEGER NOT NULL DEFAULT 0"
                )
            if "deleted_at" not in columns:
                connection.execute(
                    "ALTER TABLE analysis_runs ADD COLUMN deleted_at TEXT NULL"
                )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analysis_runs_created_at
                ON analysis_runs (created_at)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analysis_runs_owner_created_at
                ON analysis_runs (owner_user_id, created_at DESC, run_id DESC)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_run_outcomes (
                    run_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    state TEXT NOT NULL,
                    stock_id TEXT NULL,
                    failure_code TEXT NULL,
                    failure_detail TEXT NULL,
                    PRIMARY KEY (run_id, symbol),
                    FOREIGN KEY (run_id)
                        REFERENCES analysis_runs(run_id)
                        ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analysis_run_outcomes_symbol
                ON analysis_run_outcomes (symbol)
                """
            )

    def save(self, run: AnalysisRun) -> None:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT owner_user_id FROM analysis_runs WHERE run_id = ?",
                (str(run.id),),
            ).fetchone()
            if existing is not None:
                existing_owner = UUID(existing[0]) if existing[0] else None
                if existing_owner != run.owner_user_id:
                    raise ValueError("Analysis run ownership cannot be changed")

            connection.execute(
                """
                INSERT INTO analysis_runs (run_id, created_at, state, owner_user_id, outcomes_available)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    created_at = excluded.created_at,
                    state = excluded.state,
                    owner_user_id = excluded.owner_user_id,
                    outcomes_available = excluded.outcomes_available
                """,
                (
                    str(run.id),
                    run.created_at.isoformat(),
                    run.state.value,
                    str(run.owner_user_id) if run.owner_user_id else None,
                    1 if run.outcomes_available else 0,
                ),
            )
            connection.execute(
                "DELETE FROM analysis_run_outcomes WHERE run_id = ?",
                (str(run.id),),
            )
            connection.executemany(
                """
                INSERT INTO analysis_run_outcomes (
                    run_id, symbol, state, stock_id, failure_code, failure_detail
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        str(run.id),
                        outcome.symbol,
                        outcome.state.value,
                        str(outcome.stock_id) if outcome.stock_id else None,
                        outcome.failure_code,
                        outcome.failure_detail,
                    )
                    for outcome in run.outcomes
                ],
            )

    def list_runs(
        self,
        *,
        state: ExecutionState | None = None,
        owner_user_id: UUID | None = None,
        include_global: bool = False,
        before_created_at: datetime | None = None,
        before_run_id: UUID | None = None,
        limit: int = 50,
    ) -> tuple[AnalysisRun, ...]:
        query = """
            SELECT run_id, created_at, state, owner_user_id, outcomes_available
            FROM analysis_runs
        """
        parameters: list[str] = []
        conditions: list[str] = ["deleted_at IS NULL"]

        if state is not None:
            conditions.append("state = ?")
            parameters.append(state.value)

        if owner_user_id is not None:
            if include_global:
                conditions.append("(owner_user_id = ? OR owner_user_id IS NULL)")
            else:
                conditions.append("owner_user_id = ?")
            parameters.append(str(owner_user_id))

        if before_created_at is not None and before_run_id is not None:
            conditions.append(
                "(created_at < ? OR (created_at = ? AND run_id < ?))"
            )
            created_at = before_created_at.isoformat()
            parameters.extend([created_at, created_at, str(before_run_id)])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC, run_id DESC LIMIT ?"
        parameters.append(str(limit))

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
            return tuple(self._load_run_from_row(connection, row) for row in rows)

    def get(self, run_id: UUID) -> AnalysisRun | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT run_id, created_at, state, owner_user_id, outcomes_available
                FROM analysis_runs
                WHERE run_id = ?
                  AND deleted_at IS NULL
                """,
                (str(run_id),),
            ).fetchone()

            if row is None:
                return None

            return self._load_run_from_row(connection, row)

    @staticmethod
    def _load_run_from_row(
        connection: sqlite3.Connection,
        row: tuple[str, str, str, str | None, int],
    ) -> AnalysisRun:
        run_id = UUID(row[0])
        outcome_rows = connection.execute(
            """
            SELECT symbol, state, stock_id, failure_code, failure_detail
            FROM analysis_run_outcomes
            WHERE run_id = ?
            ORDER BY symbol ASC
            """,
            (str(run_id),),
        ).fetchall()

        outcomes: list[AnalysisRunOutcome] = []
        for symbol, state, stock_id, failure_code, failure_detail in outcome_rows:
            try:
                outcome_state = AnalysisRunOutcomeState(state)
                parsed_stock_id = UUID(stock_id) if stock_id else None
            except (ValueError, TypeError) as error:
                raise ValueError(
                    f"Invalid analysis run outcome data for {run_id}"
                ) from error

            if outcome_state is AnalysisRunOutcomeState.SUCCESS:
                outcomes.append(
                    AnalysisRunOutcome.success(symbol, parsed_stock_id)
                )
            else:
                if not failure_code:
                    raise ValueError(
                        f"Missing analysis run outcome failure code for {run_id}"
                    )
                outcomes.append(
                    AnalysisRunOutcome.failed(
                        symbol,
                        failure_code,
                        failure_detail,
                        parsed_stock_id,
                    )
                )

        owner_user_id = UUID(row[3]) if row[3] else None
        return AnalysisRun(
            id=run_id,
            created_at=datetime.fromisoformat(row[1]),
            state=ExecutionState(row[2]),
            owner_user_id=owner_user_id,
            outcomes=tuple(outcomes),
            outcomes_available=bool(row[4]),
        )
