from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.news.event import NewsEvent, NewsEventCategory, NewsSourceType
from app.infrastructure.persistence.sqlite_news_event_store import SQLiteNewsEventStore


def dt(day: int, hour: int = 10) -> datetime:
    return datetime(2026, 10, day, hour, tzinfo=timezone.utc)


def make_event(**changes) -> NewsEvent:
    values = {
        "event_id": uuid4(),
        "source_name": "Official Exchange",
        "source_type": NewsSourceType.EXCHANGE_DISCLOSURE,
        "source_url": "https://example.com/disclosure/1",
        "title": "Quarterly results",
        "category": NewsEventCategory.EARNINGS,
        "published_at": dt(20),
        "retrieved_at": dt(20, 11),
        "first_seen_at": dt(20, 11),
        "matched_symbols": ("egal",),
        "entity_match_confidence": Decimal("0.99"),
        "content_fingerprint": "sha256:sample-1",
    }
    values.update(changes)
    return NewsEvent(**values)


def test_news_store_round_trip_and_idempotent_replay(tmp_path) -> None:
    store = SQLiteNewsEventStore(tmp_path / "news.db")
    event = make_event()
    assert store.upsert(event)
    assert not store.upsert(event)
    reopened = SQLiteNewsEventStore(tmp_path / "news.db")
    assert reopened.get(event.event_id) == event


def test_news_store_deduplicates_content_fingerprint(tmp_path) -> None:
    store = SQLiteNewsEventStore(tmp_path / "news.db")
    first = make_event()
    second = make_event(event_id=uuid4(), source_url="https://other.example/item")
    assert store.upsert(first)
    assert not store.upsert(second)


def test_news_as_of_query_excludes_future_and_unknown_publication_time(tmp_path) -> None:
    store = SQLiteNewsEventStore(tmp_path / "news.db")
    published = make_event()
    future = make_event(
        event_id=uuid4(),
        source_url="https://example.com/future",
        title="Future report",
        published_at=dt(21),
        retrieved_at=dt(21, 11),
        first_seen_at=dt(21, 11),
        content_fingerprint="sha256:future",
    )
    undated = make_event(
        event_id=uuid4(),
        source_url="https://example.com/undated",
        title="Undated report",
        published_at=None,
        content_fingerprint="sha256:undated",
    )
    store.upsert(published)
    store.upsert(future)
    store.upsert(undated)

    results = store.query_as_of(dt(20, 12), symbol="EGAL")
    assert results == (published,)


def test_news_query_validates_limit_and_confidence(tmp_path) -> None:
    store = SQLiteNewsEventStore(tmp_path / "news.db")
    with pytest.raises(ValueError, match="between 1 and 1000"):
        store.query_as_of(dt(20), limit=0)
    with pytest.raises(ValueError, match="between zero and one"):
        store.query_as_of(dt(20), minimum_entity_confidence=Decimal("2"))
