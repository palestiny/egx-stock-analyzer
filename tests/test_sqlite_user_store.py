import sqlite3
from uuid import UUID

from app.application.identity.user_store import UserStore
from app.domain.identity.user import User, UserStatus
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore


USER_ID = UUID("00000000-0000-0000-0000-00000000000a")


def test_sqlite_user_store_persists_and_reloads_user(tmp_path):
    database_path = tmp_path / "analysis.db"
    user = User(USER_ID, UserStatus.ACTIVE)

    store: UserStore = SQLiteUserStore(database_path)
    store.save(user)

    restored = SQLiteUserStore(database_path).get(USER_ID)

    assert restored == user


def test_sqlite_user_store_updates_lifecycle_status(tmp_path):
    database_path = tmp_path / "analysis.db"
    store = SQLiteUserStore(database_path)
    store.save(User(USER_ID, UserStatus.ACTIVE))
    store.save(User(USER_ID, UserStatus.DISABLED))

    restored = store.get(USER_ID)

    assert restored == User(USER_ID, UserStatus.DISABLED)


def test_sqlite_user_store_creates_users_table_without_replacing_analysis_data(tmp_path):
    database_path = tmp_path / "analysis.db"

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE analysis_results (
                snapshot_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                analysis_date TEXT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO analysis_results (
                snapshot_id, symbol, analysis_date, payload
            )
            VALUES (?, ?, ?, ?)
            """,
            ("snapshot-1", "EGAL", "2026-09-18", "{}"),
        )

    SQLiteUserStore(database_path)

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert "users" in tables
    assert "analysis_results" in tables
    row = connection.execute(
        "SELECT symbol, analysis_date, payload FROM analysis_results"
    ).fetchone()
    assert row == ("EGAL", "2026-09-18", "{}")


def test_sqlite_user_store_returns_none_for_missing_user(tmp_path):
    store = SQLiteUserStore(tmp_path / "analysis.db")

    assert store.get(USER_ID) is None
