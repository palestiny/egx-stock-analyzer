import sqlite3
from pathlib import Path
from time import monotonic, sleep


SQLITE_BUSY_TIMEOUT_MS = 5_000


def connect_sqlite(database_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with bounded lock waiting and WAL journaling."""
    connection = sqlite3.connect(
        str(database_path),
        timeout=SQLITE_BUSY_TIMEOUT_MS / 1_000,
    )
    try:
        connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
        _ensure_wal_mode(connection)
    except Exception:
        connection.close()
        raise
    return connection



def _ensure_wal_mode(connection: sqlite3.Connection) -> None:
    """Enable WAL once, tolerating concurrent first-time database initialization."""
    mode = connection.execute("PRAGMA journal_mode").fetchone()[0].lower()
    if mode == "wal" or mode in {"memory", "off"}:
        return

    deadline = monotonic() + SQLITE_BUSY_TIMEOUT_MS / 1_000
    while True:
        try:
            mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0].lower()
            if mode == "wal":
                return
            # SQLite does not support WAL for every database mode (for example
            # in-memory databases), so retain the engine's returned mode.
            return
        except sqlite3.OperationalError as error:
            if "locked" not in str(error).lower() or monotonic() >= deadline:
                raise
            # journal_mode transitions may not honor busy_timeout. Re-read before
            # retrying because another initializer may already have enabled WAL.
            sleep(0.025)
            mode = connection.execute("PRAGMA journal_mode").fetchone()[0].lower()
            if mode == "wal":
                return
