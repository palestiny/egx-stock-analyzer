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



def test_concurrent_first_connections_enable_wal_without_lock_errors(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    database_path = tmp_path / "concurrent-first-open.db"

    def open_and_close():
        connection = connect_sqlite(database_path)
        try:
            return connection.execute("PRAGMA journal_mode").fetchone()[0].lower()
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=8) as pool:
        modes = list(pool.map(lambda _: open_and_close(), range(16)))

    assert modes == ["wal"] * 16


def test_sqlite_wal_reader_can_read_committed_snapshot_during_writer_transaction(tmp_path):
    database_path = tmp_path / "reader-writer.db"
    writer = connect_sqlite(database_path)
    reader = connect_sqlite(database_path)
    try:
        writer.execute("CREATE TABLE sample (value INTEGER)")
        writer.execute("INSERT INTO sample VALUES (1)")
        writer.commit()

        writer.execute("BEGIN IMMEDIATE")
        writer.execute("INSERT INTO sample VALUES (2)")

        assert reader.execute("SELECT value FROM sample ORDER BY value").fetchall() == [(1,)]

        writer.commit()
        assert reader.execute("SELECT value FROM sample ORDER BY value").fetchall() == [
            (1,),
            (2,),
        ]
    finally:
        reader.close()
        writer.close()


def test_sqlite_backup_can_be_restored_to_a_new_database(tmp_path):
    source_path = tmp_path / "source.db"
    backup_path = tmp_path / "backup.db"
    source = connect_sqlite(source_path)
    backup = connect_sqlite(backup_path)
    try:
        source.execute("CREATE TABLE sample (value TEXT NOT NULL)")
        source.execute("INSERT INTO sample VALUES ('restore-check')")
        source.commit()
        source.backup(backup)
    finally:
        backup.close()
        source.close()

    restored = connect_sqlite(backup_path)
    try:
        assert restored.execute("SELECT value FROM sample").fetchone() == ("restore-check",)
    finally:
        restored.close()
