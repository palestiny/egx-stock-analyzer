import json
import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4
from app.infrastructure.persistence.sqlite_connection import connect_sqlite

from app.application.market_data.acquisition import (
    AcquisitionRecord,
    AcquisitionStatus,
)
from app.application.market_data.conflict import MarketDataConflictEvent
from app.application.market_data.operational_store import MarketDataConflictError
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.timeframe import Timeframe


class SQLiteOperationalMarketDataStore:
    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = connect_sqlite(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_data_acquisitions (
                    acquisition_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    source_symbol TEXT NOT NULL,
                    stock_id TEXT NOT NULL,
                    requested_from TEXT NOT NULL,
                    requested_to TEXT NOT NULL,
                    actual_from TEXT NULL,
                    actual_to TEXT NULL,
                    requested_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    raw_artifact_hash TEXT NULL,
                    error TEXT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_data_observations (
                    stock_id TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    open TEXT NULL,
                    high TEXT NULL,
                    low TEXT NULL,
                    close TEXT NULL,
                    volume INTEGER NULL,
                    acquisition_id TEXT NOT NULL,
                    PRIMARY KEY (stock_id, timeframe, timestamp),
                    FOREIGN KEY (acquisition_id)
                        REFERENCES market_data_acquisitions(acquisition_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_data_conflicts (
                    conflict_id TEXT PRIMARY KEY,
                    stock_id TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    acquisition_id TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    existing_acquisition_id TEXT NULL,
                    existing_observation TEXT NOT NULL,
                    incoming_observation TEXT NOT NULL,
                    FOREIGN KEY (acquisition_id)
                        REFERENCES market_data_acquisitions(acquisition_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_market_data_observations_stock_time
                ON market_data_observations(stock_id, timestamp)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_market_data_acquisitions_stock_range
                ON market_data_acquisitions(stock_id, requested_from, requested_to)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_market_data_conflicts_stock_time
                ON market_data_conflicts(stock_id, timestamp)
                """
            )

    def get_daily_observations(
        self,
        stock_id: UUID,
        from_date: date,
        to_date: date,
    ) -> list[RawPriceBarObservation]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT stock_id, timeframe, timestamp, open, high, low, close, volume
                FROM market_data_observations
                WHERE stock_id = ?
                  AND timeframe = ?
                  AND date(timestamp) BETWEEN ? AND ?
                ORDER BY timestamp ASC
                """,
                (
                    str(stock_id),
                    Timeframe.DAILY.value,
                    from_date.isoformat(),
                    to_date.isoformat(),
                ),
            ).fetchall()
        return [self._observation_from_row(row) for row in rows]

    def persist_successful_acquisition(
        self,
        record: AcquisitionRecord,
        observations: list[RawPriceBarObservation],
    ) -> None:
        if record.status is not AcquisitionStatus.SUCCEEDED:
            raise ValueError("Successful persistence requires a succeeded acquisition")

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO market_data_acquisitions (
                    acquisition_id, provider, source_symbol, stock_id,
                    requested_from, requested_to, actual_from, actual_to,
                    requested_at, completed_at, status, row_count,
                    raw_artifact_hash, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._acquisition_values(record),
            )

            for incoming in observations:
                key = self._observation_key(incoming)
                existing_row = connection.execute(
                    """
                    SELECT stock_id, timeframe, timestamp, open, high, low, close,
                           volume, acquisition_id
                    FROM market_data_observations
                    WHERE stock_id = ? AND timeframe = ? AND timestamp = ?
                    """,
                    key,
                ).fetchone()

                if existing_row is None:
                    connection.execute(
                        """
                        INSERT INTO market_data_observations (
                            stock_id, timeframe, timestamp, open, high, low, close,
                            volume, acquisition_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        self._observation_values(incoming, record.acquisition_id),
                    )
                    continue

                existing = self._observation_from_row(existing_row[:8])
                if existing == incoming:
                    continue

                detected_at = datetime.now(timezone.utc)
                event = MarketDataConflictEvent(
                    conflict_id=uuid4(),
                    stock_id=record.stock_id,
                    timeframe=key[1],
                    timestamp=datetime.fromisoformat(key[2]),
                    acquisition_id=record.acquisition_id,
                    detected_at=detected_at,
                    existing_acquisition_id=UUID(existing_row[8]) if existing_row[8] else None,
                    existing_observation=existing,
                    incoming_observation=incoming,
                )
                conflicted = record.conflicted(
                    completed_at=detected_at,
                    error=f"Market data conflict for identity {key}",
                )
                connection.execute(
                    """
                    UPDATE market_data_acquisitions
                    SET completed_at = ?, status = ?, error = ?
                    WHERE acquisition_id = ?
                    """,
                    (
                        conflicted.completed_at.isoformat(),
                        conflicted.status.value,
                        conflicted.error,
                        str(record.acquisition_id),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO market_data_conflicts (
                        conflict_id, stock_id, timeframe, timestamp,
                        acquisition_id, detected_at, existing_acquisition_id,
                        existing_observation, incoming_observation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(event.conflict_id),
                        str(event.stock_id),
                        event.timeframe,
                        event.timestamp.isoformat(),
                        str(event.acquisition_id),
                        event.detected_at.isoformat(),
                        str(event.existing_acquisition_id)
                        if event.existing_acquisition_id
                        else None,
                        self._serialize_observation(event.existing_observation),
                        self._serialize_observation(event.incoming_observation),
                    ),
                )
                connection.commit()
                raise MarketDataConflictError(
                    key,
                    existing,
                    incoming,
                    acquisition_id=record.acquisition_id,
                    conflict_event=event,
                )

    def save_acquisition(self, record: AcquisitionRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO market_data_acquisitions (
                    acquisition_id, provider, source_symbol, stock_id,
                    requested_from, requested_to, actual_from, actual_to,
                    requested_at, completed_at, status, row_count,
                    raw_artifact_hash, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._acquisition_values(record),
            )

    def get_acquisitions(
        self,
        stock_id: UUID,
        from_date: date,
        to_date: date,
    ) -> list[AcquisitionRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT acquisition_id, provider, source_symbol, stock_id,
                       requested_from, requested_to, actual_from, actual_to,
                       requested_at, completed_at, status, row_count,
                       raw_artifact_hash, error
                FROM market_data_acquisitions
                WHERE stock_id = ?
                  AND requested_from <= ?
                  AND requested_to >= ?
                ORDER BY requested_at ASC, acquisition_id ASC
                """,
                (str(stock_id), to_date.isoformat(), from_date.isoformat()),
            ).fetchall()
        return [self._acquisition_from_row(row) for row in rows]

    def get_conflict_events(
        self,
        stock_id: UUID,
        from_date: date,
        to_date: date,
    ) -> list[MarketDataConflictEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT conflict_id, stock_id, timeframe, timestamp,
                       acquisition_id, detected_at, existing_acquisition_id,
                       existing_observation, incoming_observation
                FROM market_data_conflicts
                WHERE stock_id = ?
                  AND date(timestamp) BETWEEN ? AND ?
                ORDER BY detected_at ASC, conflict_id ASC
                """,
                (str(stock_id), from_date.isoformat(), to_date.isoformat()),
            ).fetchall()
        return [
            MarketDataConflictEvent(
                conflict_id=UUID(row[0]),
                stock_id=UUID(row[1]),
                timeframe=row[2],
                timestamp=datetime.fromisoformat(row[3]),
                acquisition_id=UUID(row[4]),
                detected_at=datetime.fromisoformat(row[5]),
                existing_acquisition_id=UUID(row[6]) if row[6] else None,
                existing_observation=self._deserialize_observation(row[7]),
                incoming_observation=self._deserialize_observation(row[8]),
            )
            for row in rows
        ]

    @staticmethod
    def _observation_key(
        observation: RawPriceBarObservation,
    ) -> tuple[str, str, str]:
        if observation.stock_id is None or observation.timeframe is None or observation.timestamp is None:
            raise ValueError("Operational market data observations require identity fields")
        return (
            str(observation.stock_id),
            observation.timeframe.value,
            observation.timestamp.isoformat(),
        )

    @staticmethod
    def _observation_values(
        observation: RawPriceBarObservation,
        acquisition_id: UUID,
    ) -> tuple:
        key = SQLiteOperationalMarketDataStore._observation_key(observation)
        return (
            *key,
            str(observation.open) if observation.open is not None else None,
            str(observation.high) if observation.high is not None else None,
            str(observation.low) if observation.low is not None else None,
            str(observation.close) if observation.close is not None else None,
            observation.volume,
            str(acquisition_id),
        )

    @staticmethod
    def _observation_from_row(row: tuple) -> RawPriceBarObservation:
        return RawPriceBarObservation(
            stock_id=UUID(row[0]),
            timeframe=Timeframe(row[1]),
            timestamp=datetime.fromisoformat(row[2]),
            open=Decimal(row[3]) if row[3] is not None else None,
            high=Decimal(row[4]) if row[4] is not None else None,
            low=Decimal(row[5]) if row[5] is not None else None,
            close=Decimal(row[6]) if row[6] is not None else None,
            volume=row[7],
        )

    @staticmethod
    def _serialize_observation(observation: RawPriceBarObservation) -> str:
        stock_id, timeframe, timestamp = SQLiteOperationalMarketDataStore._observation_key(observation)
        return json.dumps(
            {
                "stock_id": stock_id,
                "timeframe": timeframe,
                "timestamp": timestamp,
                "open": str(observation.open) if observation.open is not None else None,
                "high": str(observation.high) if observation.high is not None else None,
                "low": str(observation.low) if observation.low is not None else None,
                "close": str(observation.close) if observation.close is not None else None,
                "volume": observation.volume,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _deserialize_observation(payload: str) -> RawPriceBarObservation:
        data = json.loads(payload)
        return RawPriceBarObservation(
            stock_id=UUID(data["stock_id"]),
            timeframe=Timeframe(data["timeframe"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            open=Decimal(data["open"]) if data["open"] is not None else None,
            high=Decimal(data["high"]) if data["high"] is not None else None,
            low=Decimal(data["low"]) if data["low"] is not None else None,
            close=Decimal(data["close"]) if data["close"] is not None else None,
            volume=data["volume"],
        )

    @staticmethod
    def _acquisition_values(record: AcquisitionRecord) -> tuple:
        return (
            str(record.acquisition_id),
            record.provider,
            record.source_symbol,
            str(record.stock_id),
            record.requested_from.isoformat(),
            record.requested_to.isoformat(),
            record.actual_from.isoformat() if record.actual_from else None,
            record.actual_to.isoformat() if record.actual_to else None,
            record.requested_at.isoformat(),
            record.completed_at.isoformat(),
            record.status.value,
            record.row_count,
            record.raw_artifact_hash,
            record.error,
        )

    @staticmethod
    def _acquisition_from_row(row: tuple) -> AcquisitionRecord:
        return AcquisitionRecord(
            acquisition_id=UUID(row[0]),
            provider=row[1],
            source_symbol=row[2],
            stock_id=UUID(row[3]),
            requested_from=date.fromisoformat(row[4]),
            requested_to=date.fromisoformat(row[5]),
            actual_from=date.fromisoformat(row[6]) if row[6] else None,
            actual_to=date.fromisoformat(row[7]) if row[7] else None,
            requested_at=datetime.fromisoformat(row[8]),
            completed_at=datetime.fromisoformat(row[9]),
            status=AcquisitionStatus(row[10]),
            row_count=row[11],
            raw_artifact_hash=row[12],
            error=row[13],
        )
