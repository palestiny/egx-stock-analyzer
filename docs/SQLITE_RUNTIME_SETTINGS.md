# SQLite runtime settings

All application SQLite stores use the shared connection helper. Connections have a 5-second connection timeout and `PRAGMA busy_timeout` of 5000 ms, and file-backed databases use WAL journaling to improve reader/writer concurrency.

WAL does not make SQLite multi-writer: writes remain serialized. Callers should keep write transactions short and retry only operations whose idempotency semantics are known. The database must be on a filesystem that supports SQLite locking correctly; network shares and unsupported synced folders are not assumed safe.

The connection helper is intended for the application's file-backed databases and supports in-memory connections for tests. A later deployment review should confirm backup/checkpoint behavior and the target filesystem.
