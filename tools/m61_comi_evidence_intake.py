#!/usr/bin/env python3
"""Deterministic acceptance report for a real COMI M61 dataset artifact.

This tool validates an already acquired dataset. It never downloads data,
creates synthetic evidence, or modifies the supplied dataset.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

from app.infrastructure.historical_dataset.loader import (
    HistoricalDatasetIntegrityError,
    HistoricalDatasetLoader,
)

COMI_SYMBOL = "COMI"
EVALUATION_START = date(2021, 1, 1)
EVALUATION_END = date(2025, 12, 31)
WARMUP_START = date(2020, 1, 1)
REQUIRED_WARMUP = 252
EGX_TIMEZONE = ZoneInfo("Africa/Cairo")


def _resolve_symbol_mapping(mappings: tuple[str, ...], symbol: str) -> UUID | None:
    """Resolve exactly one well-formed source-symbol mapping."""
    prefix = symbol.strip().upper() + "->"
    matches = [
        mapping.replace(" ", "").upper()
        for mapping in mappings
        if mapping.replace(" ", "").upper().startswith(prefix)
    ]
    if len(matches) != 1:
        return None

    _, raw_stock_id = matches[0].split("->", 1)
    try:
        return UUID(raw_stock_id)
    except ValueError:
        return None


def _coverage_counts(timestamps) -> tuple[list[date], int, int]:
    """Count unique Cairo-local sessions in warm-up and evaluation windows."""
    dates = sorted({timestamp.astimezone(EGX_TIMEZONE).date() for timestamp in timestamps})
    warmup = sum(value < EVALUATION_START for value in dates)
    evaluation = sum(EVALUATION_START <= value <= EVALUATION_END for value in dates)
    return dates, warmup, evaluation


_REQUIRED_LICENSE_USES = {"local_storage", "historical_research", "backtesting"}
_ALLOWED_CORPORATE_ACTION_CONVENTIONS = {
    "raw-as-published",
    "unadjusted",
    "split-adjusted",
    "split-and-dividend-adjusted",
    "total-return-adjusted",
    "vendor-adjusted",
}


def _license_attestation_is_explicit(notes: str) -> bool:
    """Require a structured owner attestation instead of treating any note as proof."""
    fields: dict[str, str] = {}
    for part in notes.split(";"):
        key, separator, value = part.partition("=")
        if separator:
            fields[key.strip().casefold()] = value.strip()

    evidence_reference = fields.get("evidence_reference", "")
    permitted_uses = {
        item.strip().casefold()
        for item in fields.get("permitted_uses", "").split(",")
        if item.strip()
    }
    return (
        fields.get("status", "").casefold() == "verified"
        and evidence_reference.casefold() not in {"", "unknown", "tbd", "none", "n/a"}
        and _REQUIRED_LICENSE_USES.issubset(permitted_uses)
        and fields.get("redistribution", "").casefold() in {"allowed", "prohibited"}
    )


def _corporate_action_convention_is_explicit(value: str) -> bool:
    return value.strip().casefold() in _ALLOWED_CORPORATE_ACTION_CONVENTIONS


def _financial_availability_years(snapshots) -> list[int]:
    return sorted(
        {
            item.available_at.year
            for item in snapshots
            if EVALUATION_START <= item.available_at <= EVALUATION_END
        }
    )


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

    market_provenance = manifest.market_observations.provenance
    financial_provenance = manifest.financial_snapshots.provenance

    comi_stock_id = _resolve_symbol_mapping(
        market_provenance.symbol_mappings,
        COMI_SYMBOL,
    )
    financial_stock_id = _resolve_symbol_mapping(
        financial_provenance.symbol_mappings,
        COMI_SYMBOL,
    )

    report["checks"]["comi_identity_mapping"] = (
        "PASS" if comi_stock_id is not None else "FAIL"
    )
    report["checks"]["financial_source_mapping"] = (
        "PASS"
        if financial_stock_id == comi_stock_id and financial_stock_id is not None
        else "FAIL"
    )

    if comi_stock_id is None:
        report["errors"].append(
            "Market provenance must contain exactly one valid COMI -> internal stock mapping."
        )
        return report

    if financial_stock_id != comi_stock_id:
        report["errors"].append(
            "Financial provenance COMI mapping must resolve to the same internal stock identity."
        )

    comi_market = [item for item in market if item.stock_id == comi_stock_id]
    comi_financial = [item for item in financial if item.stock_id == comi_stock_id]

    report["checks"]["market_observation_identity"] = (
        "PASS" if comi_market else "FAIL"
    )
    report["checks"]["financial_identity_mapping"] = (
        "PASS" if comi_financial else "FAIL"
    )

    if not comi_market:
        report["errors"].append("No market observations match the mapped COMI stock identity.")
        return report
    if not comi_financial:
        report["errors"].append(
            "No financial snapshots match the mapped COMI stock identity."
        )

    # The 252-observation warm-up is counted across the full pre-evaluation
    # history, not only calendar year 2020. Use distinct Cairo-local sessions so
    # duplicate rows and timezone offsets cannot inflate coverage.
    dates, warmup, evaluation = _coverage_counts(
        [item.timestamp for item in comi_market]
    )

    report["coverage"] = {
        "first_date": min(dates).isoformat(),
        "last_date": max(dates).isoformat(),
        "warmup_observations": warmup,
        "evaluation_observations": evaluation,
    }

    report["checks"]["252_warmup"] = "PASS" if warmup >= REQUIRED_WARMUP else "FAIL"
    report["checks"]["evaluation_window"] = (
        "PASS"
        if min(dates) <= WARMUP_START
        and max(dates) >= EVALUATION_END
        and evaluation
        else "FAIL"
    )
    report["checks"]["corporate_action_convention"] = (
        "PASS"
        if _corporate_action_convention_is_explicit(
            market_provenance.corporate_action_convention
        )
        else "FAIL"
    )
    report["checks"]["market_licensing_attestation"] = (
        "PASS"
        if _license_attestation_is_explicit(market_provenance.licensing_notes)
        else "FAIL"
    )
    report["checks"]["financial_licensing_attestation"] = (
        "PASS"
        if _license_attestation_is_explicit(financial_provenance.licensing_notes)
        else "FAIL"
    )
    availability_years = _financial_availability_years(comi_financial)
    required_years = list(range(EVALUATION_START.year, EVALUATION_END.year + 1))
    missing_availability_years = [
        year for year in required_years if year not in availability_years
    ]
    report["financial_coverage"] = {
        "availability_years": availability_years,
        "missing_availability_years": missing_availability_years,
    }
    report["checks"]["point_in_time_financial_coverage"] = (
        "PASS" if not missing_availability_years else "FAIL"
    )
    report["checks"]["financial_artifact"] = "PASS" if comi_financial else "FAIL"

    failures = [
        name for name, result in report["checks"].items() if result != "PASS"
    ]
    report["status"] = "ACCEPTED" if not failures else "REJECTED"
    if failures:
        report["errors"].append("Failed checks: " + ", ".join(failures))
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
