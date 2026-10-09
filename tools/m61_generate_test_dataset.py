"""Generate a deterministic, explicitly synthetic dataset for end-to-end testing.

This data is not EGX market history and must never be used to evaluate or claim
investment-strategy performance. It exists to unblock application testing while
a real, permitted historical dataset is still unavailable.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import date, datetime, time, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

EGX_TIMEZONE = ZoneInfo("Africa/Cairo")
PROVIDER = "synthetic-test-generator"
SOURCE_URL = "synthetic://m61-test-dataset"
COHORT = (
    ("COMI", "Commercial International Bank", 65.0),
    ("EGAL", "Egypt Aluminum", 120.0),
    ("SWDY", "Elsewedy Electric", 35.0),
    ("ETEL", "Telecom Egypt", 28.0),
    ("EAST", "Eastern Company", 22.0),
    ("TMGH", "Talaat Moustafa Group", 55.0),
    ("PHDC", "Palm Hills Developments", 4.0),
    ("FWRY", "Fawry for Banking Technology and Electronic Payments", 6.0),
    ("EFID", "Edita Food Industries", 18.0),
    ("HRHO", "EFG Holding", 20.0),
)
MARKET_COLUMNS = (
    "stock_id", "timeframe", "timestamp", "open", "high", "low",
    "close", "volume", "source",
)
FINANCIAL_COLUMNS = (
    "stock_id", "period_end", "available_at", "revenue", "net_income",
    "current_assets", "current_liabilities", "source", "revision",
)


def _stock_id(symbol: str) -> str:
    return str(uuid5(
        NAMESPACE_URL,
        f"https://github.com/palestiny/egx-stock-analyzer/stocks/{symbol}",
    ))


def _weekdays(start: date, end: date) -> list[date]:
    days: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _market_rows(start: date, end: date) -> list[dict[str, str]]:
    days = _weekdays(start, end)
    rows: list[dict[str, str]] = []
    for symbol, _name, base_price in sorted(COHORT, key=lambda item: _stock_id(item[0])):
        previous_close = base_price
        seed = sum(ord(character) for character in symbol)
        for index, session in enumerate(days):
            cycle = (
                0.00035
                + 0.0028 * math.sin((index + seed) / 9.0)
                + 0.0011 * math.cos((index + seed) / 31.0)
            )
            close = max(0.1, previous_close * (1.0 + cycle))
            open_price = max(
                0.1,
                previous_close * (1.0 + 0.0018 * math.sin((index + seed) / 5.0)),
            )
            spread = 0.004 + 0.002 * (1.0 + math.sin((index + seed) / 13.0)) / 2.0
            high = max(open_price, close) * (1.0 + spread)
            low = min(open_price, close) * (1.0 - spread)
            timestamp = datetime.combine(session, time(12, 0), tzinfo=EGX_TIMEZONE)
            volume = 100_000 + ((index * 7919 + seed * 101) % 4_000_000)
            rows.append({
                "stock_id": _stock_id(symbol),
                "timeframe": "1d",
                "timestamp": timestamp.isoformat(),
                "open": f"{open_price:.4f}",
                "high": f"{high:.4f}",
                "low": f"{low:.4f}",
                "close": f"{close:.4f}",
                "volume": str(volume),
                "source": PROVIDER,
            })
            previous_close = close
    return rows


def _financial_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for symbol, _name, base_price in sorted(COHORT, key=lambda item: _stock_id(item[0])):
        seed = sum(ord(character) for character in symbol)
        base_revenue = int(base_price * 2_000_000 + seed * 10_000)
        for year in range(2018, 2026):
            period_end = date(year, 12, 31)
            available_at = period_end + timedelta(days=60)
            scale = year - 2017
            revenue = base_revenue * scale
            net_income = revenue * (0.06 + (seed % 9) / 100)
            assets = revenue * 0.42
            liabilities = revenue * 0.21
            rows.append({
                "stock_id": _stock_id(symbol),
                "period_end": period_end.isoformat(),
                "available_at": available_at.isoformat(),
                "revenue": f"{revenue:.2f}",
                "net_income": f"{net_income:.2f}",
                "current_assets": f"{assets:.2f}",
                "current_liabilities": f"{liabilities:.2f}",
                "source": PROVIDER,
                "revision": "synthetic-v1",
            })
    return rows


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> bytes:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path.read_bytes()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _artifact(
    path: str,
    raw: bytes,
    row_count: int,
    start: str,
    end: str,
) -> dict[str, object]:
    digest = _sha256(raw)
    return {
        "path": path,
        "sha256": digest,
        "row_count": row_count,
        "coverage": {"start": start, "end": end, "stock_count": len(COHORT)},
        "provenance": {
            "provider": PROVIDER,
            "source_url": SOURCE_URL,
            "acquired_at": datetime.now(EGX_TIMEZONE).isoformat(),
            "symbol_mappings": [
                f"{symbol} -> {_stock_id(symbol)}" for symbol, _name, _price in COHORT
            ],
            "corporate_action_convention": "synthetic-no-corporate-actions",
            "missing_data_findings": [
                "Synthetic weekdays only; EGX holidays, suspensions, and real trading calendars are not modeled."
            ],
            "exclusions": [],
            "licensing_notes": "Synthetic test data only; not sourced from or representative of real EGX prices or financials.",
            "transformation_manifest": "Deterministic formula-based synthetic OHLCV and annual financial records; no real observations.",
            "raw_source_evidence": {
                "reference": path,
                "sha256": digest,
                "retention": "Generated synthetic test artifact; no external source response.",
            },
        },
    }


def build_test_dataset(output_dir: Path, start: date, end: date) -> dict[str, object]:
    if start > end:
        raise ValueError("start date cannot be after end date")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("Output directory must be empty or absent")
    output_dir.mkdir(parents=True, exist_ok=True)

    market_rows = _market_rows(start, end)
    financial_rows = _financial_rows()
    market_bytes = _write_csv(output_dir / "market_observations.csv", MARKET_COLUMNS, market_rows)
    financial_bytes = _write_csv(
        output_dir / "financial_snapshots.csv", FINANCIAL_COLUMNS, financial_rows
    )
    sessions = _weekdays(start, end)
    market_start = datetime.combine(sessions[0], time(12, 0), tzinfo=EGX_TIMEZONE).isoformat()
    market_end = datetime.combine(sessions[-1], time(12, 0), tzinfo=EGX_TIMEZONE).isoformat()
    manifest = {
        "dataset_id": "m61-synthetic-test-only",
        "dataset_version": "synthetic-v1",
        "schema_version": "3",
        "market_observations_artifact": _artifact(
            "market_observations.csv", market_bytes, len(market_rows), market_start, market_end
        ),
        "financial_snapshots_artifact": _artifact(
            "financial_snapshots.csv",
            financial_bytes,
            len(financial_rows),
            date(2018, 12, 31).isoformat(),
            date(2025, 12, 31).isoformat(),
        ),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "dataset_id": manifest["dataset_id"],
        "dataset_version": manifest["dataset_version"],
        "symbols": len(COHORT),
        "market_rows": len(market_rows),
        "financial_rows": len(financial_rows),
        "market_start": market_start,
        "market_end": market_end,
        "output_dir": str(output_dir),
        "warning": "SYNTHETIC TEST DATA ONLY — NOT REAL EGX HISTORY; DO NOT USE FOR INVESTMENT EVALUATION.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--from-date", type=date.fromisoformat, default=date(2019, 1, 1))
    parser.add_argument("--to-date", type=date.fromisoformat, default=date(2025, 12, 31))
    args = parser.parse_args()
    print(json.dumps(build_test_dataset(args.output_dir, args.from_date, args.to_date), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
