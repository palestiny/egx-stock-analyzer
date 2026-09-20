import sqlite3
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

from app.application.analysis.result_store import (
    AnalysisResultPersistenceError,
    AnalysisResultRecord,
    AnalysisRunRecord,
)
from app.application.analysis.stock_analysis import StockAnalysisResult
from app.domain.execution import ExecutionState
from app.infrastructure.persistence.analysis_result_serializer import (
    deserialize_analysis_result,
    serialize_analysis_result,
)


class SQLiteAnalysisResultStore:
    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            columns = [
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(analysis_results)"
                ).fetchall()
            ]

            if not columns:
                self._create_history_table(connection)
            elif "snapshot_id" not in columns:
                self._migrate_latest_only_table(connection)

            columns = [row[1] for row in connection.execute("PRAGMA table_info(analysis_results)").fetchall()]
            if "analysis_run_id" not in columns:
                connection.execute("ALTER TABLE analysis_results ADD COLUMN analysis_run_id TEXT NULL")
            connection.execute("CREATE TABLE IF NOT EXISTS analysis_runs (run_id TEXT PRIMARY KEY, analysis_date TEXT NULL, state TEXT NOT NULL)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_analysis_results_run ON analysis_results (analysis_run_id)")
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_analysis_results_run_symbol ON analysis_results (analysis_run_id, symbol) WHERE analysis_run_id IS NOT NULL")

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analysis_results_symbol_date
                ON analysis_results (symbol, analysis_date)
                """
            )

    @staticmethod
    def _create_history_table(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_results (
                snapshot_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                analysis_date TEXT NULL,
                payload TEXT NOT NULL,
                analysis_run_id TEXT NULL
            )
            """
        )

    @staticmethod
    def _migrate_latest_only_table(connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            """
            SELECT symbol, analysis_date, payload
            FROM analysis_results
            """
        ).fetchall()

        connection.execute(
            """
            CREATE TABLE analysis_results_v2 (
                snapshot_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                analysis_date TEXT NULL,
                payload TEXT NOT NULL
            )
            """
        )

        connection.executemany(
            """
            INSERT INTO analysis_results_v2 (
                snapshot_id,
                symbol,
                analysis_date,
                payload
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (str(uuid4()), symbol, analysis_date, payload)
                for symbol, analysis_date, payload in rows
            ],
        )

        connection.execute("DROP TABLE analysis_results")
        connection.execute(
            "ALTER TABLE analysis_results_v2 RENAME TO analysis_results"
        )

    def save(
        self,
        symbol: str,
        result: StockAnalysisResult,
        analysis_date: date | None = None,
        analysis_run_id: UUID | None = None,
    ) -> None:
        payload = serialize_analysis_result(result)
        analysis_date_value = (
            analysis_date.isoformat() if analysis_date is not None else None
        )

        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO analysis_results (
                        snapshot_id,
                        symbol,
                        analysis_date,
                        payload,
                        analysis_run_id
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        symbol,
                        analysis_date_value,
                        payload,
                        str(analysis_run_id) if analysis_run_id is not None else None,
                    ),
                )
        except sqlite3.Error as error:
            raise AnalysisResultPersistenceError(
                f"Could not persist analysis result for {symbol}"
            ) from error

    def create_analysis_run(self, run_id: UUID, analysis_date: date | None) -> None:
        try:
            with self._connect() as connection:
                connection.execute("INSERT INTO analysis_runs (run_id, analysis_date, state) VALUES (?, ?, ?)", (str(run_id), analysis_date.isoformat() if analysis_date else None, ExecutionState.CREATED.value))
        except sqlite3.Error as error:
            raise AnalysisResultPersistenceError(f"Could not create analysis run {run_id}") from error

    def update_analysis_run_state(self, run_id: UUID, state: ExecutionState) -> None:
        with self._connect() as connection:
            cursor = connection.execute("UPDATE analysis_runs SET state = ? WHERE run_id = ?", (state.value, str(run_id)))
            if cursor.rowcount != 1:
                raise AnalysisResultPersistenceError(f"Unknown analysis run: {run_id}")

    def get_analysis_run(self, run_id: UUID) -> AnalysisRunRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT run_id, analysis_date, state FROM analysis_runs WHERE run_id = ?", (str(run_id),)).fetchone()
        if row is None:
            return None
        return AnalysisRunRecord(run_id=UUID(row[0]), analysis_date=date.fromisoformat(row[1]) if row[1] else None, state=ExecutionState(row[2]))

    def get_run_snapshots(self, run_id: UUID) -> tuple[AnalysisResultRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute("SELECT snapshot_id, symbol, analysis_date, payload, analysis_run_id FROM analysis_results WHERE analysis_run_id = ? ORDER BY symbol ASC, snapshot_id ASC", (str(run_id),)).fetchall()
        return tuple(self._to_record(row) for row in rows)

    def get(self, symbol: str) -> StockAnalysisResult | None:
        record = self.get_record(symbol)
        return record.result if record is not None else None

    def get_snapshot(self, snapshot_id: UUID) -> AnalysisResultRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT snapshot_id, symbol, analysis_date, payload, analysis_run_id
                FROM analysis_results
                WHERE snapshot_id = ?
                """,
                (str(snapshot_id),),
            ).fetchone()

        return self._to_record(row) if row is not None else None

    def get_record(self, symbol: str) -> AnalysisResultRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT snapshot_id, symbol, analysis_date, payload, analysis_run_id
                FROM analysis_results
                WHERE symbol = ?
                ORDER BY
                    analysis_date IS NULL ASC,
                    analysis_date DESC,
                    snapshot_id ASC
                LIMIT 1
                """,
                (symbol,),
            ).fetchone()

        return self._to_record(row) if row is not None else None

    def get_history(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[AnalysisResultRecord, ...]:
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValueError("start_date cannot be after end_date")

        query = """
            SELECT snapshot_id, symbol, analysis_date, payload, analysis_run_id
            FROM analysis_results
            WHERE symbol = ?
        """
        parameters: list[str] = [symbol]

        if start_date is not None:
            query += " AND analysis_date >= ?"
            parameters.append(start_date.isoformat())

        if end_date is not None:
            query += " AND analysis_date <= ?"
            parameters.append(end_date.isoformat())

        query += """
            ORDER BY
                analysis_date IS NULL ASC,
                analysis_date DESC,
                snapshot_id ASC
        """

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        return tuple(self._to_record(row) for row in rows)

    @staticmethod
    def _to_record(
        row: tuple[str, str, str | None, str, str | None],
    ) -> AnalysisResultRecord:
        snapshot_id, symbol, analysis_date_value, payload, analysis_run_id = row
        return AnalysisResultRecord(
            result=deserialize_analysis_result(payload),
            analysis_date=(
                date.fromisoformat(analysis_date_value)
                if analysis_date_value is not None
                else None
            ),
            snapshot_id=UUID(snapshot_id),
            symbol=symbol,
            analysis_run_id=UUID(analysis_run_id) if analysis_run_id is not None else None,
        )
