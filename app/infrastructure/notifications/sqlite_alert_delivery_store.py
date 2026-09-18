import sqlite3
from pathlib import Path
from uuid import UUID

from app.application.notifications.delivery_store import (
    AlertDeliveryRecord,
    AlertDeliveryStatus,
)


class SQLiteAlertDeliveryStore:
    def __init__(self, database_path: str) -> None:
        self._database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_deliveries (
                    stock_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_error TEXT NULL,
                    PRIMARY KEY (stock_id, snapshot_id, channel)
                )
                """
            )

    def get(self, stock_id: UUID, snapshot_id: UUID, channel: str) -> AlertDeliveryRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT stock_id, snapshot_id, channel, status, last_error FROM alert_deliveries WHERE stock_id = ? AND snapshot_id = ? AND channel = ?",
                (str(stock_id), str(snapshot_id), channel),
            ).fetchone()
        return self._to_record(row) if row else None

    def create_pending(self, stock_id: UUID, snapshot_id: UUID, channel: str) -> AlertDeliveryRecord:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO alert_deliveries(stock_id, snapshot_id, channel, status) VALUES (?, ?, ?, ?)",
                (str(stock_id), str(snapshot_id), channel, AlertDeliveryStatus.PENDING.value),
            )
        record = self.get(stock_id, snapshot_id, channel)
        assert record is not None
        return record

    def mark_delivered(self, stock_id: UUID, snapshot_id: UUID, channel: str) -> AlertDeliveryRecord:
        with self._connect() as connection:
            connection.execute(
                "UPDATE alert_deliveries SET status = ?, last_error = NULL WHERE stock_id = ? AND snapshot_id = ? AND channel = ?",
                (AlertDeliveryStatus.DELIVERED.value, str(stock_id), str(snapshot_id), channel),
            )
        record = self.get(stock_id, snapshot_id, channel)
        assert record is not None
        return record

    def mark_failed(self, stock_id: UUID, snapshot_id: UUID, channel: str, error: str) -> AlertDeliveryRecord:
        with self._connect() as connection:
            connection.execute(
                "UPDATE alert_deliveries SET status = ?, last_error = ? WHERE stock_id = ? AND snapshot_id = ? AND channel = ?",
                (AlertDeliveryStatus.FAILED.value, error, str(stock_id), str(snapshot_id), channel),
            )
        record = self.get(stock_id, snapshot_id, channel)
        assert record is not None
        return record

    @staticmethod
    def _to_record(row: tuple[object, ...]) -> AlertDeliveryRecord:
        return AlertDeliveryRecord(
            stock_id=UUID(str(row[0])),
            snapshot_id=UUID(str(row[1])),
            channel=str(row[2]),
            status=AlertDeliveryStatus(str(row[3])),
            last_error=str(row[4]) if row[4] is not None else None,
        )