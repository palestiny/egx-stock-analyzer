import sqlite3
from pathlib import Path
from uuid import UUID

from app.domain.identity.user import User, UserStatus


class SQLiteUserStore:
    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL
                )
                """
            )

    def save(self, user: User) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO users (id, status)
                VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET status = excluded.status
                """,
                (str(user.id), user.status.value),
            )

    def get_or_create(self, user_id: UUID, status: UserStatus) -> User:
        existing = self.get(user_id)
        if existing is not None:
            return existing
        user = User(id=user_id, status=status)
        self.save(user)
        return user

    def get(self, user_id: UUID) -> User | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, status FROM users WHERE id = ?",
                (str(user_id),),
            ).fetchone()

        if row is None:
            return None

        return User(id=UUID(row[0]), status=UserStatus(row[1]))
