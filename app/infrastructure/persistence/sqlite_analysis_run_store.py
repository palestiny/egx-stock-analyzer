import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.application.analysis.run_store import AnalysisRunStore
from app.domain.analysis_run import AnalysisRun
from app.domain.execution import ExecutionState


class SQLiteAnalysisRunStore(AnalysisRunStore):
    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    state TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analysis_runs_created_at
                ON analysis_runs (created_at)
                """
            )

    def save(self, run: AnalysisRun) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO analysis_runs (run_id, created_at, state)
                VALUES (?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    created_at = excluded.created_at,
                    state = excluded.state
                """,
                (
                    str(run.id),
                    run.created_at.isoformat(),
                    run.state.value,
                ),
            )

    def get(self, run_id: UUID) -> AnalysisRun | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT run_id, created_at, state
                FROM analysis_runs
                WHERE run_id = ?
                """,
                (str(run_id),),
            ).fetchone()

        if row is None:
            return None

        return AnalysisRun(
            id=UUID(row[0]),
            created_at=datetime.fromisoformat(row[1]),
            state=ExecutionState(row[2]),
        )
