from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.news.event import NewsEventCategory, NewsSourceType
from app.infrastructure.news.rss_news_source_adapter import RssNewsSourceAdapter


NOW = datetime(2026, 10, 26, 18, 0, tzinfo=timezone.utc)

RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Official disclosures</title>
<item><guid>disclosure-123</guid><title>EGAL announces quarterly financial results</title>
<link>https://news.example.test/egal/123</link><pubDate>Mon, 26 Oct 2026 16:00:00 +0000</pubDate>
<description>Egypt Aluminium reports earnings.</description></item>
<item><guid>old-1</guid><title>Market outlook</title><link>/market/old</link>
<pubDate>Sun, 25 Oct 2026 10:00:00 +0000</pubDate></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Feed</title>
<entry><id>tag:news.example.test,2026:42</id><title>Dividend declared for Egypt Aluminium</title>
<link href="https://news.example.test/egal/42"/>
<published>2026-10-26T17:00:00Z</published><summary>Dividend distribution</summary></entry>
</feed>"""


def adapter(payload: bytes = RSS) -> RssNewsSourceAdapter:
    return RssNewsSourceAdapter(
        source_name="Configured EGX Feed",
        source_type=NewsSourceType.EXCHANGE_DISCLOSURE,
        feed_url="https://news.example.test/feed.xml",
        symbol_names={"EGAL": "Egypt Aluminium", "COMI": "Commercial International Bank"},
        fetch_bytes=lambda url, timeout, maximum: payload,
        clock=lambda: NOW,
    )


def test_rss_adapter_extracts_point_in_time_event_without_storing_body() -> None:
    events = adapter().fetch_recent()

    assert len(events) == 2
    event = events[0]
    assert event.title == "EGAL announces quarterly financial results"
    assert event.source_url == "https://news.example.test/egal/123"
    assert event.published_at == datetime(2026, 10, 26, 16, tzinfo=timezone.utc)
    assert event.retrieved_at == NOW
    assert event.first_seen_at == NOW
    assert event.matched_symbols == ("EGAL",)
    assert event.entity_match_confidence == Decimal("0.99")
    assert event.category is NewsEventCategory.EARNINGS
    assert not hasattr(event, "description")


def test_rss_adapter_filters_before_since_and_drops_undated_items() -> None:
    events = adapter().fetch_recent(datetime(2026, 10, 26, 15, tzinfo=timezone.utc))

    assert len(events) == 1
    assert events[0].title.startswith("EGAL")


def test_rss_adapter_produces_stable_event_ids_and_fingerprints() -> None:
    first = adapter().fetch_recent()[0]
    second = adapter().fetch_recent()[0]

    assert first.event_id == second.event_id
    assert first.content_fingerprint == second.content_fingerprint


def test_atom_adapter_parses_namespaced_fields_and_classifies_dividends() -> None:
    events = adapter(ATOM).fetch_recent()

    assert len(events) == 1
    assert events[0].source_url == "https://news.example.test/egal/42"
    assert events[0].matched_symbols == ("EGAL",)
    assert events[0].entity_match_confidence == Decimal("0.90")
    assert events[0].category is NewsEventCategory.DIVIDEND


def test_adapter_rejects_non_https_feed_urls() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        RssNewsSourceAdapter(
            source_name="Untrusted",
            source_type=NewsSourceType.OTHER,
            feed_url="http://news.example.test/feed.xml",
            symbol_names={},
        )


def test_adapter_rejects_dtd_and_entity_declarations() -> None:
    unsafe = b'<!DOCTYPE rss [<!ENTITY x "boom">]><rss><channel/></rss>'
    with pytest.raises(ValueError, match="DTD and entity"):
        adapter(unsafe).fetch_recent()


def test_adapter_rejects_naive_clock() -> None:
    bad_clock = RssNewsSourceAdapter(
        source_name="Configured EGX Feed",
        source_type=NewsSourceType.EXCHANGE_DISCLOSURE,
        feed_url="https://news.example.test/feed.xml",
        symbol_names={},
        fetch_bytes=lambda url, timeout, maximum: RSS,
        clock=lambda: datetime(2026, 10, 26, 18, 0),
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        bad_clock.fetch_recent()
