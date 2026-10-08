import sqlite3

from app.infrastructure.persistence.sqlite_connection import (
    SQLITE_BUSY_TIMEOUT_MS,
    connect_sqlite,
)


def test_sqlite_connection_uses_wal_and_busy_timeout(tmp_path):
    database_path = tmp_path / "concurrency.db"

    connection = connect_sqlite(database_path)
    try:
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
    finally:
        connection.close()

    assert journal_mode.lower() == "wal"
    assert busy_timeout == SQLITE_BUSY_TIMEOUT_MS


def test_sqlite_connection_remains_usable_for_in_memory_database():
    connection = connect_sqlite(":memory:")
    try:
        connection.execute("CREATE TABLE sample (value INTEGER)")
        connection.execute("INSERT INTO sample VALUES (1)")
        assert connection.execute("SELECT value FROM sample").fetchone() == (1,)
    finally:
        connection.close()
