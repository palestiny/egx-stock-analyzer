from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence

from app.application.news.store import NewsEventStore
from app.domain.news.event import NewsEvent


class NewsSourceAdapter(Protocol):
    @property
    def source_name(self) -> str:
        ...

    def fetch_recent(self, since: datetime | None = None) -> Sequence[NewsEvent]:
        ...


@dataclass(frozen=True)
class NewsIngestionSummary:
    source_name: str
    fetched: int
    inserted: int
    duplicates: int


class NewsIngestionService:
    """Orchestrate provider-neutral event ingestion without interpreting article content."""

    def __init__(self, source: NewsSourceAdapter, store: NewsEventStore) -> None:
        self._source = source
        self._store = store

    def ingest(self, since: datetime | None = None) -> NewsIngestionSummary:
        if since is not None and (since.tzinfo is None or since.utcoffset() is None):
            raise ValueError("since must be timezone-aware")

        events = tuple(self._source.fetch_recent(since))
        inserted = 0
        duplicates = 0
        for event in events:
            if event.source_name != self._source.source_name:
                raise ValueError("event source_name does not match the configured adapter")
            if self._store.upsert(event):
                inserted += 1
            else:
                duplicates += 1

        return NewsIngestionSummary(
            source_name=self._source.source_name,
            fetched=len(events),
            inserted=inserted,
            duplicates=duplicates,
        )
