from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
from uuid import UUID

from app.application.news.store import NewsEventStore
from app.domain.news.event import NewsEvent, NewsEventCategory, NewsSourceType
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteNewsEventStore(NewsEventStore):
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
                CREATE TABLE IF NOT EXISTS news_events (
                    event_id TEXT PRIMARY KEY,
                    source_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    published_at TEXT NULL,
                    retrieved_at TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    matched_symbols_json TEXT NOT NULL,
                    entity_match_confidence TEXT NOT NULL,
                    content_fingerprint TEXT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_news_fingerprint_unique
                ON news_events(content_fingerprint)
                WHERE content_fingerprint IS NOT NULL
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_news_published_seen
                ON news_events(published_at, first_seen_at)
                """
            )

    def upsert(self, event: NewsEvent) -> bool:
        values = self._values(event)
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM news_events WHERE event_id = ?",
                (str(event.event_id),),
            ).fetchone()
            if existing is not None:
                if self._to_event(existing) != event:
                    raise ValueError("conflicting news event replay")
                return False
            if event.content_fingerprint is not None:
                duplicate = connection.execute(
                    "SELECT event_id FROM news_events WHERE content_fingerprint = ?",
                    (event.content_fingerprint,),
                ).fetchone()
                if duplicate is not None:
                    return False
            connection.execute(
                """
                INSERT INTO news_events(
                    event_id, source_name, source_type, source_url, title, category,
                    published_at, retrieved_at, first_seen_at, matched_symbols_json,
                    entity_match_confidence, content_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
        return True

    def get(self, event_id: UUID) -> NewsEvent | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM news_events WHERE event_id = ?",
                (str(event_id),),
            ).fetchone()
        return self._to_event(row) if row is not None else None

    def query_as_of(
        self,
        as_of: datetime,
        *,
        symbol: str | None = None,
        minimum_entity_confidence: Decimal = Decimal("0.8"),
        limit: int = 100,
    ) -> tuple[NewsEvent, ...]:
        self._require_aware(as_of, "as_of")
        if not minimum_entity_confidence.is_finite() or not (
            Decimal("0") <= minimum_entity_confidence <= Decimal("1")
        ):
            raise ValueError("minimum_entity_confidence must be between zero and one")
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")

        cutoff = as_of.astimezone(timezone.utc).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM news_events
                WHERE published_at IS NOT NULL
                  AND published_at <= ?
                  AND first_seen_at <= ?
                  AND CAST(entity_match_confidence AS REAL) >= ?
                ORDER BY published_at DESC, event_id ASC
                """,
                (cutoff, cutoff, float(minimum_entity_confidence)),
            ).fetchall()

        normalized_symbol = symbol.strip().upper() if symbol is not None else None
        eligible = [self._to_event(row) for row in rows]
        if normalized_symbol is not None:
            eligible = [
                event for event in eligible
                if normalized_symbol in event.matched_symbols
            ]
        return tuple(eligible[:limit])

    @staticmethod
    def _require_aware(value: datetime, field_name: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")

    @classmethod
    def _values(cls, event: NewsEvent) -> tuple[str | None, ...]:
        return (
            str(event.event_id),
            event.source_name,
            event.source_type.value,
            event.source_url,
            event.title,
            event.category.value,
            cls._timestamp(event.published_at),
            cls._timestamp(event.retrieved_at),
            cls._timestamp(event.first_seen_at),
            json.dumps(event.matched_symbols, separators=(",", ":")),
            str(event.entity_match_confidence),
            event.content_fingerprint,
        )

    @staticmethod
    def _timestamp(value: datetime | None) -> str | None:
        return value.astimezone(timezone.utc).isoformat() if value is not None else None

    @classmethod
    def _to_event(cls, row: tuple[object, ...]) -> NewsEvent:
        return NewsEvent(
            event_id=UUID(str(row[0])),
            source_name=str(row[1]),
            source_type=NewsSourceType(str(row[2])),
            source_url=str(row[3]),
            title=str(row[4]),
            category=NewsEventCategory(str(row[5])),
            published_at=datetime.fromisoformat(str(row[6])) if row[6] is not None else None,
            retrieved_at=datetime.fromisoformat(str(row[7])),
            first_seen_at=datetime.fromisoformat(str(row[8])),
            matched_symbols=tuple(json.loads(str(row[9]))),
            entity_match_confidence=Decimal(str(row[10])),
            content_fingerprint=str(row[11]) if row[11] is not None else None,
        )
