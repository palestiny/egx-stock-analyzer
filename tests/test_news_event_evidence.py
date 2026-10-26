from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.news.event import NewsEvent, NewsEventCategory, NewsSourceType


def event(**overrides) -> NewsEvent:
    values = {
        "event_id": uuid4(),
        "source_name": "Official Exchange",
        "source_type": NewsSourceType.EXCHANGE_DISCLOSURE,
        "source_url": "https://example.com/disclosure/1",
        "title": "Company disclosure",
        "category": NewsEventCategory.EARNINGS,
        "published_at": datetime(2026, 10, 20, 10, tzinfo=timezone.utc),
        "retrieved_at": datetime(2026, 10, 20, 10, 5, tzinfo=timezone.utc),
        "first_seen_at": datetime(2026, 10, 20, 10, 5, tzinfo=timezone.utc),
        "matched_symbols": ("egal",),
        "entity_match_confidence": Decimal("0.99"),
    }
    values.update(overrides)
    return NewsEvent(**values)


def test_news_event_normalizes_symbol_and_requires_point_in_time_visibility() -> None:
    item = event()
    assert item.matched_symbols == ("EGAL",)
    assert item.eligible_as_of(datetime(2026, 10, 20, 10, 6, tzinfo=timezone.utc))
    assert not item.eligible_as_of(datetime(2026, 10, 20, 10, 4, tzinfo=timezone.utc))


def test_news_without_publication_timestamp_is_not_backtest_eligible() -> None:
    item = event(published_at=None)
    assert not item.eligible_as_of(datetime(2026, 10, 21, tzinfo=timezone.utc))


def test_news_event_rejects_naive_timestamps() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        event(first_seen_at=datetime(2026, 10, 20, 10, 5))


def test_news_event_rejects_invalid_entity_match_confidence() -> None:
    with pytest.raises(ValueError, match="between zero and one"):
        event(entity_match_confidence=Decimal("1.1"))


def test_news_event_rejects_duplicate_symbols_after_normalization() -> None:
    with pytest.raises(ValueError, match="unique"):
        event(matched_symbols=("egal", "EGAL"))
