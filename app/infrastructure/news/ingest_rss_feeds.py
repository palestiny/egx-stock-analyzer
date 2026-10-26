from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any

from app.application.news.ingestion import NewsIngestionService
from app.domain.news.event import NewsSourceType
from app.infrastructure.news.rss_source import RSSFeedConfig, RSSNewsSource
from app.infrastructure.persistence.sqlite_news_event_store import SQLiteNewsEventStore


def parse_feed_configs(raw: str | None) -> tuple[RSSFeedConfig, ...]:
    if raw is None or not raw.strip():
        return ()
    try:
        values = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("EGX_NEWS_RSS_FEEDS must be valid JSON") from error
    if not isinstance(values, list):
        raise ValueError("EGX_NEWS_RSS_FEEDS must be a JSON array")

    feeds: list[RSSFeedConfig] = []
    seen_names: set[str] = set()
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            raise ValueError(f"EGX_NEWS_RSS_FEEDS item {index} must be an object")
        try:
            name = str(value["source_name"]).strip()
            url = str(value["url"]).strip()
            source_type = NewsSourceType(str(value["source_type"]))
            timeout = float(value.get("timeout_seconds", 8.0))
            feed = RSSFeedConfig(name, url, source_type, timeout)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"EGX_NEWS_RSS_FEEDS item {index} is invalid") from error
        if feed.source_name in seen_names:
            raise ValueError("EGX_NEWS_RSS_FEEDS contains duplicate source names")
        seen_names.add(feed.source_name)
        feeds.append(feed)
    return tuple(feeds)


def parse_symbol_aliases(raw: str | None) -> dict[str, tuple[str, ...]]:
    if raw is None or not raw.strip():
        return {}
    try:
        values: Any = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("EGX_NEWS_SYMBOL_ALIASES must be valid JSON") from error
    if not isinstance(values, dict):
        raise ValueError("EGX_NEWS_SYMBOL_ALIASES must be a JSON object")
    aliases: dict[str, tuple[str, ...]] = {}
    for raw_symbol, raw_values in values.items():
        symbol = str(raw_symbol).strip().upper()
        if not symbol or not isinstance(raw_values, list) or any(
            not isinstance(alias, str) or not alias.strip() for alias in raw_values
        ):
            raise ValueError("EGX_NEWS_SYMBOL_ALIASES must map symbols to arrays of non-empty strings")
        aliases[symbol] = tuple(alias.strip() for alias in raw_values)
    return aliases


def main() -> int:
    feeds = parse_feed_configs(os.getenv("EGX_NEWS_RSS_FEEDS"))
    if not feeds:
        raise SystemExit("Configure at least one licensed HTTPS feed in EGX_NEWS_RSS_FEEDS")
    aliases = parse_symbol_aliases(os.getenv("EGX_NEWS_SYMBOL_ALIASES"))
    database_path = os.getenv("EGX_ANALYSIS_DATABASE_PATH", "storage/analysis.db")
    store = SQLiteNewsEventStore(database_path)
    summaries = []
    for feed in feeds:
        service = NewsIngestionService(
            RSSNewsSource(feed, symbol_aliases=aliases),
            store,
        )
        summary = service.ingest()
        summaries.append({
            "source_name": summary.source_name,
            "fetched": summary.fetched,
            "inserted": summary.inserted,
            "duplicates": summary.duplicates,
        })
    print(json.dumps({"feeds": summaries}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
