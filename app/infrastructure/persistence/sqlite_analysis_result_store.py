import sqlite3
from datetime import date
from pathlib import Path

from app.application.analysis.result_store import AnalysisResultRecord
from app.application.analysis.stock_analysis import StockAnalysisResult
from app.infrastructure.persistence.analysis_result_serializer import (
    deserialize_analysis_result,
    serialize_analysis_result,
)


class SQLiteAnalysisResultStore:
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = str(database_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_results (
                    symbol TEXT PRIMARY KEY,
                    analysis_date TEXT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def save(
        self,
        symbol: str,
        result: StockAnalysisResult,
        analysis_date: date | None = None,
    ) -> None:
        payload = serialize_analysis_result(result)
        analysis_date_value = (
            analysis_date.isoformat() if analysis_date is not None else None
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO analysis_results (symbol, analysis_date, payload)
                VALUES (?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    analysis_date = excluded.analysis_date,
                    payload = excluded.payload
                """,
                (symbol, analysis_date_value, payload),
            )

    def get(self, symbol: str) -> StockAnalysisResult | None:
        record = self.get_record(symbol)
        return record.result if record is not None else None

    def get_record(self, symbol: str) -> AnalysisResultRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT analysis_date, payload
                FROM analysis_results
                WHERE symbol = ?
                """,
                (symbol,),
            ).fetchone()

        if row is None:
            return None

        analysis_date = (
            date.fromisoformat(row[0]) if row[0] is not None else None
        )
        return AnalysisResultRecord(
            result=deserialize_analysis_result(row[1]),
            analysis_date=analysis_date,
        )
