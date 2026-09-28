#!/usr/bin/env python3
"""M61 Yahoo Finance historical acquisition tool.

Acquisition tooling only. It produces local evidence artifacts; it does not
register Yahoo as the production historical-data provider and it does not
claim licensing/redistribution rights.

The raw artifact is a deterministic CSV serialization of the rows returned by
the yfinance history call. It must be treated as acquisition evidence, not as
an original Yahoo-delivered download file.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import yfinance as yf

from app.infrastructure.stocks.m61_catalog import create_m61_stock_catalog

SOURCE = "Yahoo Finance / yfinance"
TICKER_SUFFIX = ".CA"
DEFAULT_FROM = "2020-01-01"
DEFAULT_TO_EXCLUSIVE = "2026-01-01"


def normalize_history_rows(rows: list[dict], stock_id: UUID) -> list[dict]:
    normalized: list[dict] = []
    for row in rows:
        timestamp = row["Date"]
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        timestamp = timestamp.astimezone(UTC)
        normalized.append(
            {
                "stock_id": str(stock_id),
                "timeframe": "1d",
                "timestamp": timestamp.isoformat(),
                "open": Decimal(str(row["Open"])),
                "high": Decimal(str(row["High"])),
                "low": Decimal(str(row["Low"])),
                "close": Decimal(str(row["Close"])),
                "volume": Decimal(str(row["Volume"])),
                "source": SOURCE,
            }
        )
    return sorted(normalized, key=lambda row: row["timestamp"])


def write_market_artifact(rows: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "stock_id",
        "timeframe",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def write_raw_artifact(rows: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["Date", "Open", "High", "Low", "Close", "Volume"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            timestamp = row["Date"]
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)
            writer.writerow(
                {
                    "Date": timestamp.astimezone(UTC).isoformat(),
                    "Open": row["Open"],
                    "High": row["High"],
                    "Low": row["Low"],
                    "Close": row["Close"],
                    "Volume": row["Volume"],
                }
            )
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_stock_id(symbol: str) -> UUID:
    stock = create_m61_stock_catalog().get(symbol)
    if stock is None:
        raise ValueError(f"Symbol is outside the bounded M61 cohort: {symbol}")
    return stock.id


def acquire(
    symbol: str,
    stock_id: UUID,
    output_dir: Path,
    from_date: str,
    to_date: str,
) -> dict:
    ticker = f"{symbol}{TICKER_SUFFIX}"
    history = yf.Ticker(ticker).history(
        start=from_date,
        end=to_date,
        interval="1d",
        auto_adjust=False,
    )
    if history.empty:
        raise RuntimeError(f"No Yahoo Finance history returned for {ticker}")

    records = history.reset_index().to_dict("records")
    normalized = normalize_history_rows(records, stock_id)

    raw_path = write_raw_artifact(records, output_dir / "raw" / f"{symbol}.csv")
    market_path = write_market_artifact(
        normalized, output_dir / "normalized" / "market_observations.csv"
    )

    dates = [row["timestamp"] for row in normalized]
    manifest = {
        "provider": "Yahoo Finance",
        "client": "yfinance",
        "source_symbol": ticker,
        "internal_symbol": symbol,
        "stock_id": str(stock_id),
        "requested_window": {"from": from_date, "to_exclusive": to_date},
        "acquired_at": datetime.now(UTC).isoformat(),
        "row_count": len(normalized),
        "coverage": {"start": dates[0], "end": dates[-1]},
        "raw_artifact": {
            "path": str(raw_path),
            "sha256": sha256(raw_path),
            "note": "CSV serialization of yfinance history response; not an original Yahoo-delivered file.",
        },
        "normalized_artifact": {
            "path": str(market_path),
            "sha256": sha256(market_path),
        },
        "corporate_action_convention": "raw-as-published; auto_adjust=False",
        "licensing_notes": "NOT VERIFIED; acquisition candidate only. Do not redistribute until terms are reviewed.",
    }
    manifest_path = output_dir / "acquisition.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Acquire M61 historical data from Yahoo Finance."
    )
    parser.add_argument("--symbol", default="COMI")
    parser.add_argument("--from-date", default=DEFAULT_FROM)
    parser.add_argument("--to-date", default=DEFAULT_TO_EXCLUSIVE)
    parser.add_argument("--output-dir", type=Path, default=Path("m61-yahoo-acquisition"))
    args = parser.parse_args()

    stock_id = resolve_stock_id(args.symbol)
    manifest = acquire(
        args.symbol,
        stock_id,
        args.output_dir,
        args.from_date,
        args.to_date,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
