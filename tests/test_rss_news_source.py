from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.news.event import NewsEventCategory, NewsSourceType
from app.infrastructure.news.rss_source import RSSFeedConfig, RSSNewsSource


RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>EGAL announces quarterly financial results</title>
    <link>https://news.example/items/egal-results</link>
    <guid>egal-results-1</guid>
    <pubDate>Mon, 26 Oct 2026 10:00:00 GMT</pubDate>
    <description>This body must not be stored.</description>
  </item>
  <item>
    <title>General market update</title>
    <link>https://news.example/items/market-update</link>
    <guid>market-update-1</guid>
    <pubDate>Mon, 26 Oct 2026 11:00:00 GMT</pubDate>
  </item>
</channel></rss>"""


def source(*, now: datetime | None = None, payload: bytes = RSS) -> RSSNewsSource:
    config = RSSFeedConfig(
        source_name="Test financial feed",
        url="https://news.example/rss.xml",
        source_type=NewsSourceType.FINANCIAL_MEDIA,
    )
    fixed_now = now or datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
    return RSSNewsSource(
        config,
        symbol_aliases={"EGAL": ("Egypt Aluminum",)},
        fetch_bytes=lambda url, timeout: payload,
        clock=lambda: fixed_now,
    )


def test_rss_source_normalizes_metadata_without_storing_article_body() -> None:
    events = source().fetch_recent()

    assert len(events) == 2
    event = events[0]
    assert event.source_name == "Test financial feed"
    assert event.source_type is NewsSourceType.FINANCIAL_MEDIA
    assert event.category is NewsEventCategory.EARNINGS
    assert event.matched_symbols == ("EGAL",)
    assert event.entity_match_confidence == Decimal("0.99")
    assert event.published_at == datetime(2026, 10, 26, 10, tzinfo=timezone.utc)
    assert event.first_seen_at == datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
    assert "body" not in event.title.lower()


def test_rss_source_has_stable_ids_but_fresh_retrieval_timestamps() -> None:
    first = source(now=datetime(2026, 10, 26, 12, tzinfo=timezone.utc)).fetch_recent()
    second = source(now=datetime(2026, 10, 26, 13, tzinfo=timezone.utc)).fetch_recent()

    assert first[0].event_id == second[0].event_id
    assert first[0].retrieved_at != second[0].retrieved_at
    assert first[0].content_fingerprint == second[0].content_fingerprint


def test_rss_source_filters_by_timezone_aware_since() -> None:
    result = source().fetch_recent(datetime(2026, 10, 26, 10, 30, tzinfo=timezone.utc))
    assert len(result) == 1
    assert result[0].title == "General market update"


def test_rss_source_rejects_naive_since_and_naive_clock() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        source().fetch_recent(datetime(2026, 10, 26, 10))

    bad_clock = source(now=datetime(2026, 10, 26, 12))
    with pytest.raises(ValueError, match="timezone-aware"):
        bad_clock.fetch_recent()


def test_rss_source_rejects_invalid_xml() -> None:
    with pytest.raises(ValueError, match="invalid XML"):
        source(payload=b"<rss><channel>").fetch_recent()


def test_rss_feed_config_requires_https_and_bounded_timeout() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        RSSFeedConfig("Feed", "http://news.example/rss", NewsSourceType.FINANCIAL_MEDIA)
    with pytest.raises(ValueError, match="timeout_seconds"):
        RSSFeedConfig("Feed", "https://news.example/rss", NewsSourceType.FINANCIAL_MEDIA, 100)
