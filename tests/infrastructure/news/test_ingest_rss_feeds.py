from datetime import datetime, timezone

import pytest

from app.application.news.ingestion import NewsIngestionSummary
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.news.ingest_rss_feeds import parse_since, run_ingestion


def test_parse_since_accepts_timezone_aware_iso_timestamp() -> None:
    assert parse_since("2026-10-25T00:00:00Z") == datetime(
        2026, 10, 25, tzinfo=timezone.utc
    )


@pytest.mark.parametrize("value", ["", "2026-10-25T00:00:00", "not-a-date"])
def test_parse_since_rejects_empty_invalid_or_timezone_naive_values(value: str) -> None:
    with pytest.raises(ValueError):
        parse_since(value)


def test_run_ingestion_requires_explicit_feed_configuration() -> None:
    config = InfrastructureConfig(operator_token="operator-token")
    runtime_created = False

    def runtime_factory(**kwargs):
        nonlocal runtime_created
        runtime_created = True
        raise AssertionError("runtime must not be created without a feed")

    with pytest.raises(ValueError, match="EGX_NEWS_RSS_URL"):
        run_ingestion(
            config=config,
            runtime_factory=runtime_factory,
            stock_catalog_factory=lambda: object(),
            yfinance_module=object(),
        )

    assert runtime_created is False


def test_run_ingestion_invokes_service_and_closes_runtime() -> None:
    expected = NewsIngestionSummary(
        source_name="Verified feed",
        fetched=3,
        inserted=2,
        duplicates=1,
    )
    since = datetime(2026, 10, 25, tzinfo=timezone.utc)

    class FakeService:
        received_since = None

        def ingest(self, value):
            self.received_since = value
            return expected

    class FakeRuntime:
        def __init__(self):
            self.news_ingestion_service = FakeService()
            self.closed = False

        def close(self):
            self.closed = True

    runtime = FakeRuntime()
    captured = {}

    def runtime_factory(**kwargs):
        captured.update(kwargs)
        return runtime

    config = InfrastructureConfig(
        operator_token="operator-token",
        news_rss_feed_url="https://example.com/feed.xml",
        news_rss_source_name="Verified feed",
    )
    result = run_ingestion(
        since,
        config=config,
        runtime_factory=runtime_factory,
        stock_catalog_factory=lambda: "catalog",
        yfinance_module="fake-yfinance",
    )

    assert result == expected
    assert runtime.news_ingestion_service.received_since == since
    assert runtime.closed is True
    assert captured["stock_catalog"] == "catalog"
    assert captured["config"] is config
    assert captured["yfinance_module"] == "fake-yfinance"
