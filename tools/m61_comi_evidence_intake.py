#!/usr/bin/env python3
"""Deterministic acceptance report for a real COMI M61 dataset artifact.

This tool validates an already acquired dataset. It never downloads data,
creates synthetic evidence, or modifies the supplied dataset.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from app.infrastructure.historical_dataset.loader import (
    HistoricalDatasetIntegrityError,
    HistoricalDatasetLoader,
)

COMI_SYMBOL = "COMI"
EVALUATION_START = date(2021, 1, 1)
EVALUATION_END = date(2025, 12, 31)
WARMUP_START = date(2020, 1, 1)
REQUIRED_WARMUP = 252


def build_report(root: Path) -> dict:
    loader = HistoricalDatasetLoader(root)
    report = {
        "status": "REJECTED",
        "dataset": str(root),
        "checks": {},
        "errors": [],
    }

    try:
        manifest = loader.load_manifest()
        loader.verify_raw_source_evidence()
        market = loader.load_market_observations()
        financial = loader.load_financial_snapshots()
    except (HistoricalDatasetIntegrityError, OSError, ValueError) as exc:
        report["errors"].append(str(exc))
        return report

    report["checks"]["manifest"] = "PASS"
    report["checks"]["raw_source_evidence"] = "PASS"

    comi_market = [item for item in market if item.source.strip()]
    # The immutable dataset currently carries internal UUIDs; source identity is
    # accepted only when the manifest explicitly records a COMI mapping.
    mappings = (
        manifest.market_observations.provenance.symbol_mappings
        if manifest.market_observations.provenance
        else ()
    )
    has_comi_mapping = any(COMI_SYMBOL in mapping.upper() for mapping in mappings)
    report["checks"]["comi_identity_mapping"] = "PASS" if has_comi_mapping else "FAIL"

    dates_by_stock: dict[str, list[date]] = defaultdict(list)
    for item in comi_market:
        dates_by_stock[str(item.stock_id)].append(item.timestamp.date())

    if not has_comi_mapping:
        report["errors"].append("No explicit COMI source-symbol mapping in market provenance.")
        return report

    if len(dates_by_stock) != 1:
        report["errors"].append("COMI intake must resolve to exactly one internal stock identity.")
        return report

    dates = dates_by_stock[next(iter(dates_by_stock))]
    warmup = sum(WARMUP_START <= d < EVALUATION_START for d in dates)
    evaluation = sum(EVALUATION_START <= d <= EVALUATION_END for d in dates)

    report["coverage"] = {
        "first_date": min(dates).isoformat() if dates else None,
        "last_date": max(dates).isoformat() if dates else None,
        "warmup_observations": warmup,
        "evaluation_observations": evaluation,
    }

    report["checks"]["252_warmup"] = "PASS" if warmup >= REQUIRED_WARMUP else "FAIL"
    report["checks"]["evaluation_window"] = (
        "PASS"
        if dates and min(dates) <= WARMUP_START and max(dates) >= EVALUATION_END and evaluation
        else "FAIL"
    )

    provenance = manifest.market_observations.provenance
    report["checks"]["corporate_action_convention"] = (
        "PASS" if provenance and provenance.corporate_action_convention.strip() else "FAIL"
    )
    report["checks"]["licensing_notes"] = (
        "PASS" if provenance and provenance.licensing_notes.strip() else "FAIL"
    )

    failures = [name for name, result in report["checks"].items() if result != "PASS"]
    report["status"] = "ACCEPTED" if not failures else "REJECTED"
    if failures:
        report["errors"].append("Failed checks: " + ", ".join(failures))
    # Financial artifacts are required by the M61 contract; their presence and
    # generic PIT-safe shape are validated by load_financial_snapshots().
    report["checks"]["financial_artifact"] = "PASS" if financial else "FAIL"
    if not financial:
        report["status"] = "REJECTED"
        report["errors"].append("Financial snapshot artifact is empty.")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate COMI evidence for M61 acceptance.")
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    report = build_report(args.dataset)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "ACCEPTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
