"""Explicit operator-triggered RSS/Atom news ingestion command.

Configure EGX_NEWS_RSS_URL only after verifying the feed's availability and usage rights.
This command does not schedule polling and does not claim that a configured feed is official.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from typing import Any, Callable

from app.application.news.ingestion import NewsIngestionSummary
from app.application.stocks.catalog import StockCatalog
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.runtime import InfrastructureRuntime, create_infrastructure_runtime
from app.infrastructure.stocks.development_catalog import create_development_stock_catalog


def parse_since(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValueError("--since cannot be empty")
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("--since must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--since must include a timezone, for example Z or +03:00")
    return parsed


def run_ingestion(
    since: datetime | None = None,
    *,
    config: InfrastructureConfig | None = None,
    runtime_factory: Callable[..., InfrastructureRuntime] = create_infrastructure_runtime,
    stock_catalog_factory: Callable[[], StockCatalog] = create_development_stock_catalog,
    yfinance_module: Any | None = None,
) -> NewsIngestionSummary:
    if since is not None and (since.tzinfo is None or since.utcoffset() is None):
        raise ValueError("since must be timezone-aware")

    effective_config = config or InfrastructureConfig.from_environment()
    if not effective_config.news_rss_feed_url:
        raise ValueError(
            "EGX_NEWS_RSS_URL must be configured with a verified HTTPS feed URL"
        )
    if not effective_config.operator_token or not effective_config.operator_token.strip():
        raise ValueError("EGX_OPERATOR_TOKEN must be configured")

    if yfinance_module is None:
        import yfinance as yfinance_module

    runtime = runtime_factory(
        stock_catalog=stock_catalog_factory(),
        yfinance_module=yfinance_module,
        config=effective_config,
    )
    try:
        service = runtime.news_ingestion_service
        if service is None:
            raise RuntimeError("news ingestion is not configured in the infrastructure runtime")
        return service.ingest(since)
    finally:
        runtime.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest normalized news metadata from one explicitly configured RSS/Atom feed."
    )
    parser.add_argument(
        "--since",
        help="optional ISO-8601 publication cutoff with timezone, e.g. 2026-10-25T00:00:00Z",
    )
    arguments = parser.parse_args()
    try:
        summary = run_ingestion(parse_since(arguments.since))
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))
    print(json.dumps(asdict(summary), sort_keys=True))


if __name__ == "__main__":
    main()
