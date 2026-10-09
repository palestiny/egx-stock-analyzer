#!/usr/bin/env python3
"""Inspect a downloaded historical OHLCV CSV without modifying or accepting it.

This is a pre-ingestion evidence tool. It does not download data, transform prices,
infer exchange holidays, or claim that source licensing/coverage is accepted.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from tools.m61_market_validation import (
    validate_history_points,
    validate_m61_evaluation_window,
)

EGX_TIMEZONE = ZoneInfo("Africa/Cairo")

ALIASES = {
    "date": ("date", "trading date", "timestamp", "datetime"),
    "open": ("open", "opening price"),
    "high": ("high", "day high"),
    "low": ("low", "day low"),
    "close": ("close", "closing price", "last"),
    "volume": ("volume", "shares traded", "traded volume"),
}


def _column_map(fieldnames: list[str] | None) -> dict[str, str]:
    if not fieldnames:
        raise ValueError("CSV has no header row")
    normalized: dict[str, list[str]] = {}
    for field in fieldnames:
        normalized.setdefault(field.strip().casefold(), []).append(field)
    result: dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        matches = [
            original
            for alias in aliases
            for original in normalized.get(alias.casefold(), [])
        ]
        if len(matches) != 1:
            if not matches:
                raise ValueError(f"Missing required CSV column for {canonical}: {aliases}")
            raise ValueError(f"Ambiguous CSV columns for {canonical}: {matches}")
        result[canonical] = matches[0]
    return result


def _canonical_date(value: str) -> str:
    raw = value.strip()
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        pass

    try:
        timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"Unsupported date value: {value!r}; expected ISO date or timezone-aware timestamp"
        ) from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Timestamp values must include an explicit timezone")
    return timestamp.astimezone(EGX_TIMEZONE).date().isoformat()


def _canonical_number(value: str) -> str:
    # CSV producers may format large values with thousands separators.
    raw = value.strip().replace(",", "")
    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric value: {value!r}") from exc
    if not parsed.is_finite():
        raise ValueError(f"Non-finite numeric value: {value!r}")
    return format(parsed, "f")


def inspect_csv(path: Path, symbol: str, provider: str, source_reference: str) -> dict[str, Any]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 or UTF-8 with BOM") from exc

    reader = csv.DictReader(io.StringIO(decoded, newline=""))
    columns = _column_map(reader.fieldnames)
    points: list[dict[str, str]] = []
    row_errors: list[str] = []
    for index, row in enumerate(reader, start=2):
        if None in row:
            row_errors.append(f"row[{index}]: extra values beyond CSV header")
            continue
        try:
            point = {"date": _canonical_date(row[columns["date"]] or "")}
            for field in ("open", "high", "low", "close", "volume"):
                point[field] = _canonical_number(row[columns[field]] or "")
            points.append(point)
        except (ValueError, TypeError) as exc:
            row_errors.append(f"row[{index}]: {exc}")

    findings = validate_history_points(points) + validate_m61_evaluation_window(points)
    dates = sorted({date.fromisoformat(point["date"]) for point in points})
    return {
        "status": "CANDIDATE_ONLY",
        "acceptance_claim": False,
        "provider": provider,
        "symbol": symbol.strip().upper(),
        "source_reference": source_reference,
        "artifact": {
            "filename": path.name,
            "byte_count": len(raw),
            "sha256": digest,
            "row_count": len(points) + len(row_errors),
            "valid_row_count": len(points),
        },
        "columns": {"source_headers": reader.fieldnames, "mapped": columns},
        "coverage": {
            "first_date": min(dates).isoformat() if dates else None,
            "last_date": max(dates).isoformat() if dates else None,
            "warmup_observations_before_2021": sum(item < date(2021, 1, 1) for item in dates),
            "evaluation_observations_2021_2025": sum(
                date(2021, 1, 1) <= item <= date(2025, 12, 31) for item in dates
            ),
        },
        "validation_findings": findings,
        "row_errors": row_errors,
        "source_license_verified": False,
        "corporate_action_convention_verified": False,
        "point_in_time_financial_data_included": False,
        "next_gate": (
            "Verify source terms and adjustment semantics, reconcile gaps and identity, "
            "and acquire point-in-time financial snapshots before creating an accepted manifest."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a downloaded M61 daily OHLCV CSV.")
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--source-reference", required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    try:
        report = inspect_csv(args.csv_file, args.symbol, args.provider, args.source_reference)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "REJECTED", "error": str(exc)}, indent=2))
        return 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.report:
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 1 if report["row_errors"] or report["validation_findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
