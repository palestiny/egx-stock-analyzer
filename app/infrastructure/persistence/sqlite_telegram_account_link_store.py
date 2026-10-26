from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.application.notifications.telegram_account_linking import (
    TelegramAccountLinkStore,
    TelegramChatAlreadyLinked,
)
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteTelegramAccountLinkStore(TelegramAccountLinkStore):
    """Single-use Telegram linking challenges and verified chat bindings."""

    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_link_challenges (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    consumed_at TEXT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_telegram_link_challenges_user
                ON telegram_link_challenges(user_id, expires_at)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_account_links (
                    user_id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL UNIQUE,
                    linked_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_account_link_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    chat_id_hash TEXT NULL
                )
                """
            )

    def create_challenge(
        self,
        user_id: UUID,
        token_hash: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> None:
        self._require_aware(created_at, "created_at")
        self._require_aware(expires_at, "expires_at")
        if expires_at <= created_at:
            raise ValueError("challenge expiry must be after creation")
        if not token_hash.strip():
            raise ValueError("token hash is required")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO telegram_link_challenges(
                    token_hash, user_id, created_at, expires_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    token_hash,
                    str(user_id),
                    created_at.isoformat(),
                    expires_at.isoformat(),
                ),
            )

    def consume_challenge(
        self,
        token_hash: str,
        chat_id: str,
        now: datetime,
    ) -> UUID | None:
        self._require_aware(now, "now")
        if not chat_id.strip():
            raise ValueError("Telegram chat ID cannot be empty")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT user_id, expires_at, consumed_at
                FROM telegram_link_challenges
                WHERE token_hash = ?
                """,
                (token_hash,),
            ).fetchone()
            if row is None:
                return None
            user_id = UUID(str(row[0]))
            if row[2] is not None:
                linked = connection.execute(
                    "SELECT chat_id FROM telegram_account_links WHERE user_id = ?",
                    (str(user_id),),
                ).fetchone()
                if linked is not None and str(linked[0]) == chat_id.strip():
                    return user_id
                return None
            expires_at = datetime.fromisoformat(str(row[1]))
            if expires_at <= now:
                return None

            existing_chat_owner = connection.execute(
                "SELECT user_id FROM telegram_account_links WHERE chat_id = ?",
                (chat_id.strip(),),
            ).fetchone()
            if (
                existing_chat_owner is not None
                and str(existing_chat_owner[0]) != str(user_id)
            ):
                raise TelegramChatAlreadyLinked(
                    "Telegram chat is already linked to another account"
                )

            previous = connection.execute(
                "SELECT chat_id FROM telegram_account_links WHERE user_id = ?",
                (str(user_id),),
            ).fetchone()
            if previous is not None and str(previous[0]) != chat_id.strip():
                previous_chat = str(previous[0])
                connection.execute(
                    """
                    INSERT INTO telegram_account_link_events(
                        user_id, event, occurred_at, chat_id_hash
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        str(user_id),
                        "UNLINKED_FOR_RELINK",
                        now.isoformat(),
                        self._hash_chat_id(previous_chat),
                    ),
                )

            connection.execute(
                """
                INSERT INTO telegram_account_links(user_id, chat_id, linked_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    chat_id = excluded.chat_id,
                    linked_at = excluded.linked_at
                """,
                (str(user_id), chat_id.strip(), now.isoformat()),
            )
            connection.execute(
                """
                UPDATE telegram_link_challenges SET consumed_at = ?
                WHERE token_hash = ? AND consumed_at IS NULL
                """,
                (now.isoformat(), token_hash),
            )
            connection.execute(
                """
                INSERT INTO telegram_account_link_events(
                    user_id, event, occurred_at, chat_id_hash
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    str(user_id),
                    "LINKED",
                    now.isoformat(),
                    self._hash_chat_id(chat_id.strip()),
                ),
            )
        return user_id

    def get_chat_id(self, user_id: UUID) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT chat_id FROM telegram_account_links WHERE user_id = ?",
                (str(user_id),),
            ).fetchone()
        return str(row[0]) if row else None

    def unlink(self, user_id: UUID, occurred_at: datetime) -> bool:
        self._require_aware(occurred_at, "occurred_at")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT chat_id FROM telegram_account_links WHERE user_id = ?",
                (str(user_id),),
            ).fetchone()
            if row is None:
                return False
            connection.execute(
                "DELETE FROM telegram_account_links WHERE user_id = ?",
                (str(user_id),),
            )
            connection.execute(
                """
                INSERT INTO telegram_account_link_events(
                    user_id, event, occurred_at, chat_id_hash
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    str(user_id),
                    "UNLINKED",
                    occurred_at.isoformat(),
                    self._hash_chat_id(str(row[0])),
                ),
            )
        return True

    @staticmethod
    def _hash_chat_id(chat_id: str) -> str:
        return hashlib.sha256(chat_id.encode("utf-8")).hexdigest()

    @staticmethod
    def _require_aware(value: datetime, field_name: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")
