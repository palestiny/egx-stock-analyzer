#!/usr/bin/env python3
"""Summarize per-symbol coverage from the private archive's quality-audit JSON.

This tool reports observed counts only. It does not repair data, infer official
EGX listing coverage, or decide whether a symbol is suitable for trading.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def build_report(source: dict[str, Any]) -> dict[str, Any]:
    per_symbol = source.get("per_symbol")
    if not isinstance(per_symbol, dict) or not per_symbol:
        raise ValueError("input must contain a non-empty per_symbol object")

    symbols: list[dict[str, Any]] = []
    for raw_symbol, raw_stats in per_symbol.items():
        symbol = str(raw_symbol).strip().upper()
        if not symbol or not isinstance(raw_stats, dict):
            raise ValueError(f"invalid per_symbol entry: {raw_symbol!r}")

        try:
            rows = int(raw_stats["rows"])
            valid = int(raw_stats["valid_ohlc_rows"])
            invalid = int(raw_stats["invalid_ohlc_rows"])
            first_date = str(raw_stats["first_session_date"])
            last_date = str(raw_stats["last_session_date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid coverage fields for {symbol}") from exc

        if rows < 0 or valid < 0 or invalid < 0 or valid + invalid != rows:
            raise ValueError(f"inconsistent row counts for {symbol}")
        if not first_date or not last_date:
            raise ValueError(f"missing date coverage for {symbol}")
        valid_pct = (valid / rows * 100.0) if rows else None
        symbols.append({
            "symbol": symbol,
            "rows": rows,
            "valid_ohlc_rows": valid,
            "invalid_ohlc_rows": invalid,
            "valid_ohlc_pct": round(valid_pct, 2) if valid_pct is not None else None,
            "first_session_date": first_date,
            "last_session_date": last_date,
        })

    symbols.sort(key=lambda item: (-item["valid_ohlc_rows"], item["symbol"]))
    total_rows = sum(item["rows"] for item in symbols)
    total_valid = sum(item["valid_ohlc_rows"] for item in symbols)
    total_invalid = sum(item["invalid_ohlc_rows"] for item in symbols)
    return {
        "schema_version": 1,
        "report": "per_symbol_archive_coverage",
        "status": "completed",
        "source_audit_date": source.get("audited_at_utc"),
        "source_dataset_path": source.get("dataset_path"),
        "symbol_count": len(symbols),
        "total_rows": total_rows,
        "valid_ohlc_rows": total_valid,
        "invalid_ohlc_rows": total_invalid,
        "valid_ohlc_pct": round(total_valid / total_rows * 100.0, 2) if total_rows else None,
        "symbols_sorted_by_valid_rows_desc": symbols,
        "limitations": [
            "Counts summarize the supplied quality-audit JSON; the price archive itself is not re-read.",
            "Structurally valid OHLC rows are not proof of source accuracy or official EGX listing coverage.",
            "No missing sessions are inferred and no prices are repaired or adjusted.",
            "This report does not decide trading eligibility or change strategy ranking.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Data-quality-audit JSON from the private archive")
    parser.add_argument("--output", required=True, type=Path, help="Path for the generated coverage JSON")
    args = parser.parse_args()
    source = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(source, dict):
        raise ValueError("input JSON root must be an object")
    report = build_report(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "symbol_count": report["symbol_count"],
        "total_rows": report["total_rows"],
        "valid_ohlc_rows": report["valid_ohlc_rows"],
        "invalid_ohlc_rows": report["invalid_ohlc_rows"],
        "valid_ohlc_pct": report["valid_ohlc_pct"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
