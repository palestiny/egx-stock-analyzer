#!/usr/bin/env python3
"""Bounded Yahoo ticker-variant diagnostic; never writes or prints price rows.

This is an exploratory symbol-mapping check only. Provider terms, retention rights,
and point-in-time financial evidence remain unverified; no result is accepted.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.m61_free_market_probe import probe_ticker

SYMBOL = "COMI"
TICKER_VARIANTS = ("COMI.CA", "COMI.EG", "COMI.EGX", "COMI.EY", "COMI")


def _safe_summary(report: dict[str, Any]) -> dict[str, Any]:
    observed = report.get("observed", {})
    return {
        "symbol": report.get("symbol"),
        "ticker": report.get("ticker"),
        "http_status": report.get("status_code"),
        "instrument_type": observed.get("instrument_type"),
        "currency": observed.get("currency"),
        "exchange_timezone": observed.get("exchange_timezone"),
        "row_count": observed.get("row_count"),
        "first_date": observed.get("first_date"),
        "last_date": observed.get("last_date"),
        "validation_findings_total": observed.get("validation_findings_total"),
        "validation_finding_counts": observed.get("validation_finding_counts"),
        "raw_artifact_persisted": False,
        "price_values_in_report": False,
        "acceptance": {
            "status": "CANDIDATE_ONLY",
            "source_terms_verified": False,
            "long_term_storage_rights_verified": False,
            "point_in_time_financials_included": False,
            "eligible_for_strategy_v0": False,
        },
    }


def run_variant_probe() -> dict[str, Any]:
    reports = [
        _safe_summary(probe_ticker(SYMBOL, ticker, False, Path(".")))
        for ticker in TICKER_VARIANTS
    ]
    return {
        "provider": "Yahoo Finance chart endpoint",
        "purpose": "COMI ticker-variant diagnostic only",
        "variants_tested": list(TICKER_VARIANTS),
        "created_at_utc": datetime.now(UTC).isoformat(),
        "results": reports,
        "raw_prices_saved": False,
        "source_terms_verified": False,
        "dataset_accepted": False,
    }


def main() -> int:
    report = run_variant_probe()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
