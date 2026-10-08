import sqlite3
from pathlib import Path


SQLITE_BUSY_TIMEOUT_MS = 5_000


def connect_sqlite(database_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with bounded lock waiting and WAL journaling."""
    connection = sqlite3.connect(
        str(database_path),
        timeout=SQLITE_BUSY_TIMEOUT_MS / 1_000,
    )
    try:
        connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
        connection.execute("PRAGMA journal_mode = WAL")
    except Exception:
        connection.close()
        raise
    return connection
