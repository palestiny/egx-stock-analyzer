#!/usr/bin/env python3
"""Flag large price discontinuities in a normalized EGX OHLCV CSV archive.

Flags are for manual review only. The tool does not adjust prices or infer
whether a move is caused by a corporate action, bad data, or a real market move.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import TextIO

REQUIRED_COLUMNS = ("symbol", "session_date", "open", "high", "low", "close", "volume")


def _open_text(path: Path) -> TextIO:
    return gzip.open(path, "rt", encoding="utf-8-sig", newline="") if path.suffix == ".gz" else path.open("r", encoding="utf-8-sig", newline="")


def audit(path: Path, threshold: float = 0.20) -> dict[str, object]:
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold must be a finite number greater than zero")

    bars: dict[str, list[dict[str, object]]] = defaultdict(list)
    seen: set[tuple[str, date]] = set()
    duplicate_rows = 0
    rejected_rows = 0

    with _open_text(path) as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in REQUIRED_COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("missing required columns: " + ", ".join(missing))
        for row in reader:
            try:
                symbol = (row.get("symbol") or "").strip().upper()
                day = date.fromisoformat((row.get("session_date") or "").strip())
                values = {name: float(row[name]) for name in ("open", "high", "low", "close", "volume")}
                if not symbol or any(not math.isfinite(value) for value in values.values()):
                    raise ValueError("empty symbol or non-finite numeric value")
                if any(values[name] <= 0 for name in ("open", "high", "low", "close")) or values["volume"] < 0:
                    raise ValueError("non-positive OHLC or negative volume")
                if values["high"] < max(values["open"], values["close"], values["low"]) or values["low"] > min(values["open"], values["close"], values["high"]):
                    raise ValueError("inconsistent OHLC bounds")
            except (KeyError, TypeError, ValueError, OverflowError):
                rejected_rows += 1
                continue
            identity = (symbol, day)
            if identity in seen:
                duplicate_rows += 1
                continue
            seen.add(identity)
            bars[symbol].append({"date": day.isoformat(), **values})

    flags: list[dict[str, object]] = []
    for symbol, rows in sorted(bars.items()):
        rows.sort(key=lambda item: str(item["date"]))
        for index in range(1, len(rows)):
            previous, current = rows[index - 1], rows[index]
            previous_close = float(previous["close"])
            close_change = float(current["close"]) / previous_close - 1.0
            overnight_gap = float(current["open"]) / previous_close - 1.0
            if abs(close_change) >= threshold or abs(overnight_gap) >= threshold:
                flags.append({
                    "symbol": symbol,
                    "previous_date": previous["date"],
                    "date": current["date"],
                    "previous_close": previous_close,
                    "open": current["open"],
                    "high": current["high"],
                    "low": current["low"],
                    "close": current["close"],
                    "volume": current["volume"],
                    "close_to_close_change": round(close_change, 8),
                    "overnight_gap": round(overnight_gap, 8),
                    "threshold": threshold,
                    "review_note": "Manual review only; raw prices are unchanged and the cause is unverified.",
                })

    counts = Counter(str(flag["symbol"]) for flag in flags)
    return {
        "schema_version": 1,
        "audit": "large_close_to_close_or_overnight_gap_discontinuities",
        "status": "completed",
        "input": str(path),
        "threshold_fraction": threshold,
        "input_rows": len(seen) + duplicate_rows + rejected_rows,
        "usable_unique_rows": len(seen),
        "symbols": len(bars),
        "duplicate_rows_skipped": duplicate_rows,
        "rejected_rows": rejected_rows,
        "flag_count": len(flags),
        "flags_by_symbol": dict(sorted(counts.items())),
        "flags": flags,
        "limitations": [
            "A flag is not proof of incorrect data or a corporate action.",
            "The audit does not adjust, delete, or repair any price.",
            "Corporate actions, source coverage, liquidity, and trading-session alignment require separate verification.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Normalized CSV or CSV.GZ file")
    parser.add_argument("--output", required=True, type=Path, help="Path for JSON report")
    parser.add_argument("--threshold", type=float, default=0.20, help="Absolute move threshold as a fraction (default: 0.20)")
    args = parser.parse_args()
    report = audit(args.input, args.threshold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "usable_unique_rows", "symbols", "flag_count", "flags_by_symbol")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
