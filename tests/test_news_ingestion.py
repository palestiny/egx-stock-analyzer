from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.news.ingestion import NewsIngestionService
from app.domain.news.event import NewsEvent, NewsEventCategory, NewsSourceType


def make_event(source_name: str = "Official Feed") -> NewsEvent:
    now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
    return NewsEvent(
        event_id=uuid4(),
        source_name=source_name,
        source_type=NewsSourceType.EXCHANGE_DISCLOSURE,
        source_url="https://example.com/disclosure",
        title="Quarterly results",
        category=NewsEventCategory.EARNINGS,
        published_at=now,
        retrieved_at=now,
        first_seen_at=now,
        matched_symbols=("EGAL",),
        entity_match_confidence=Decimal("0.99"),
        content_fingerprint=None,
    )


class FakeSource:
    source_name = "Official Feed"

    def __init__(self, events):
        self.events = tuple(events)
        self.received_since = None

    def fetch_recent(self, since=None):
        self.received_since = since
        return self.events


class FakeStore:
    def __init__(self):
        self.events = {}

    def upsert(self, event):
        if event.event_id in self.events:
            if self.events[event.event_id] != event:
                raise ValueError("conflicting news event replay")
            return False
        self.events[event.event_id] = event
        return True

    def get(self, event_id):
        return self.events.get(event_id)

    def query_as_of(self, as_of, *, symbol=None, minimum_entity_confidence=Decimal("0.8"), limit=100):
        return ()


def test_ingestion_counts_insertions_and_duplicate_replays() -> None:
    event = make_event()
    source = FakeSource((event, event))
    store = FakeStore()

    result = NewsIngestionService(source, store).ingest()

    assert (result.fetched, result.inserted, result.duplicates) == (2, 1, 1)
    assert result.source_name == "Official Feed"


def test_ingestion_passes_timezone_aware_since_to_adapter() -> None:
    since = datetime(2026, 10, 25, tzinfo=timezone.utc)
    source = FakeSource(())
    result = NewsIngestionService(source, FakeStore()).ingest(since)

    assert source.received_since == since
    assert result.fetched == 0


def test_ingestion_rejects_naive_since_before_calling_adapter() -> None:
    source = FakeSource(())
    with pytest.raises(ValueError, match="timezone-aware"):
        NewsIngestionService(source, FakeStore()).ingest(datetime(2026, 10, 25))


def test_ingestion_rejects_events_claiming_another_source() -> None:
    source = FakeSource((make_event("Different Source"),))
    with pytest.raises(ValueError, match="does not match"):
        NewsIngestionService(source, FakeStore()).ingest()
