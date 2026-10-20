#!/usr/bin/env python3
"""Exploratory cross-sectional technical diagnostics for an existing EGX OHLCV archive.

This tool deliberately does not call the production BUY/SELL classifier, does not
use fundamentals, and does not claim that a signal is profitable. It reports
transparent forward-return comparisons so the available dataset can be explored
without waiting for a fully accepted M61 fundamentals package.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TextIO

REQUIRED_COLUMNS = ("symbol", "session_date", "open", "high", "low", "close", "volume")
HORIZONS = (1, 3, 5, 10)
MIN_HISTORY = 20


@dataclass(frozen=True)
class Bar:
    symbol: str
    session_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


def _finite_number(value: str, field: str, row_number: int) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"row {row_number}: invalid {field}") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"row {row_number}: {field} must be finite and non-negative")
    return number


def read_bars(path: Path) -> tuple[list[Bar], dict[str, object]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        missing = [column for column in REQUIRED_COLUMNS if column not in headers]
        if missing:
            raise ValueError("missing required columns: " + ", ".join(missing))
        seen: set[tuple[str, date]] = set()
        bars: list[Bar] = []
        invalid_ohlc = 0
        invalid_rows = 0
        duplicate_keys = 0
        input_rows = 0
        invalid_samples: list[dict[str, object]] = []
        for row_number, row in enumerate(reader, start=2):
            input_rows += 1
            symbol = (row.get("symbol") or "").strip().upper()
            try:
                session_date = date.fromisoformat((row.get("session_date") or "").strip())
                if not symbol:
                    raise ValueError(f"row {row_number}: empty symbol")
                open_price = _finite_number(row.get("open", ""), "open", row_number)
                high = _finite_number(row.get("high", ""), "high", row_number)
                low = _finite_number(row.get("low", ""), "low", row_number)
                close = _finite_number(row.get("close", ""), "close", row_number)
                volume = _finite_number(row.get("volume", ""), "volume", row_number)
            except ValueError as exc:
                invalid_rows += 1
                if len(invalid_samples) < 10:
                    invalid_samples.append({"row": row_number, "reason": str(exc)})
                continue

            # Validate the row before reserving its symbol/date identity. A
            # malformed first occurrence must not suppress a later valid row.
            if high < max(open_price, low, close) or low > min(open_price, high, close):
                invalid_ohlc += 1
                if len(invalid_samples) < 10:
                    invalid_samples.append({
                        "row": row_number, "symbol": symbol,
                        "session_date": session_date.isoformat(),
                        "reason": "OHLC bounds inconsistent",
                    })
                continue

            key = (symbol, session_date)
            if key in seen:
                duplicate_keys += 1
                continue
            seen.add(key)
            bars.append(Bar(symbol, session_date, open_price, high, low, close, volume))
    bars.sort(key=lambda bar: (bar.symbol, bar.session_date))
    summary: dict[str, object] = {
        "input_rows": input_rows,
        "usable_rows": len(bars),
        "unique_symbols": len({bar.symbol for bar in bars}),
        "invalid_rows": invalid_rows,
        "invalid_ohlc_rows": invalid_ohlc,
        "duplicate_symbol_date_rows_skipped": duplicate_keys,
        "first_session_date": min((b.session_date for b in bars), default=None).isoformat() if bars else None,
        "last_session_date": max((b.session_date for b in bars), default=None).isoformat() if bars else None,
        "invalid_samples": invalid_samples,
    }
    return bars, summary


def _metrics(returns: list[float]) -> dict[str, object]:
    if not returns:
        return {"samples": 0, "mean_return_pct": None, "median_return_pct": None,
                "win_rate_pct": None, "best_return_pct": None, "worst_return_pct": None}
    return {
        "samples": len(returns),
        "mean_return_pct": round(statistics.fmean(returns) * 100, 4),
        "median_return_pct": round(statistics.median(returns) * 100, 4),
        "win_rate_pct": round(sum(value > 0 for value in returns) / len(returns) * 100, 2),
        "best_return_pct": round(max(returns) * 100, 4),
        "worst_return_pct": round(min(returns) * 100, 4),
    }


def _analyze_symbol(bars: list[Bar]) -> tuple[dict[str, dict[int, list[float]]], int]:
    bars = sorted(bars, key=lambda bar: bar.session_date)
    groups: dict[str, dict[int, list[float]]] = {
        name: {horizon: [] for horizon in HORIZONS}
        for name in ("baseline", "positive_momentum_5d", "momentum_volume_1_5x",
                     "pre_breakout_proxy")
    }
    signals = 0
    closes = [bar.close for bar in bars]
    highs = [bar.high for bar in bars]
    volumes = [bar.volume for bar in bars]
    for i, bar in enumerate(bars):
        # Need 20 previous bars for features, plus the future bar for the
        # shortest horizon. Signal-day close is never used as the entry price.
        if i < MIN_HISTORY or i + 1 >= len(bars):
            continue
        prior_close = closes[i - 5]
        momentum = prior_close > 0 and bar.close > prior_close
        previous_volume = volumes[i - 5:i]
        volume_mean = statistics.fmean(previous_volume) if previous_volume else 0.0
        volume_confirmed = volume_mean > 0 and bar.volume >= 1.5 * volume_mean
        prior_20_high = max(highs[i - 20:i])
        near_prior_high = prior_20_high > 0 and prior_20_high * 0.95 <= bar.close <= prior_20_high
        signal_groups = ["baseline"]
        if momentum:
            signal_groups.append("positive_momentum_5d")
        if momentum and volume_confirmed:
            signal_groups.append("momentum_volume_1_5x")
        if momentum and volume_confirmed and near_prior_high:
            signal_groups.append("pre_breakout_proxy")
            signals += 1
        for horizon in HORIZONS:
            # Entry is next session open; exit is the close on signal-session+h.
            exit_index = i + horizon
            if exit_index >= len(bars):
                continue
            entry = bars[i + 1].open
            exit_price = bars[exit_index].close
            if entry <= 0:
                continue
            forward_return = exit_price / entry - 1.0
            for group in signal_groups:
                groups[group][horizon].append(forward_return)
    return groups, signals


def analyze_bars(bars: list[Bar], input_summary: dict[str, object]) -> dict[str, object]:
    by_symbol: dict[str, list[Bar]] = defaultdict(list)
    for bar in bars:
        by_symbol[bar.symbol].append(bar)
    pooled: dict[str, dict[int, list[float]]] = {
        name: {horizon: [] for horizon in HORIZONS}
        for name in ("baseline", "positive_momentum_5d", "momentum_volume_1_5x",
                     "pre_breakout_proxy")
    }
    per_symbol: dict[str, object] = {}
    eligible_counts: dict[str, int] = {}
    for symbol, symbol_bars in sorted(by_symbol.items()):
        groups, signals = _analyze_symbol(symbol_bars)
        per_symbol[symbol] = {
            "rows": len(symbol_bars),
            "first_session_date": symbol_bars[0].session_date.isoformat(),
            "last_session_date": symbol_bars[-1].session_date.isoformat(),
            "pre_breakout_proxy_signals": signals,
            "forward_returns": {
                group: {str(h): _metrics(values[h]) for h in HORIZONS}
                for group, values in groups.items()
            },
        }
        eligible_counts[symbol] = sum(len(groups["baseline"][h]) for h in (1,))
        for group in pooled:
            for horizon in HORIZONS:
                pooled[group][horizon].extend(groups[group][horizon])
    return {
        "schema_version": 1,
        "analysis_type": "exploratory_technical_forward_return_diagnostic",
        "source_dataset_summary": input_summary,
        "methodology": {
            "momentum": "signal close > close five observations earlier",
            "volume_confirmation": "signal-day volume >= 1.5x mean volume of the preceding five observations; signal-day volume excluded from the mean",
            "pre_breakout_proxy": "positive five-observation momentum + volume confirmation + close within 5% below the highest high of the preceding 20 observations",
            "entry": "next observed session open after the signal bar closes",
            "exit": "close of the signal session plus 1, 3, 5, or 10 observed bars",
            "costs": "transaction costs, slippage, liquidity constraints, and dividends excluded",
            "adjustment_semantics": "input provider adjustment convention is not inferred or reconciled by this tool",
        },
        "pooled_forward_returns": {
            group: {str(h): _metrics(values[h]) for h in HORIZONS}
            for group, values in pooled.items()
        },
        "per_symbol": per_symbol,
        "eligible_baseline_sessions_by_symbol": eligible_counts,
        "limitations": [
            "Secondary unofficial Yahoo Finance observations; not an authoritative complete EGX universe.",
            "Rows excluded for structural OHLC defects are not repaired or backfilled.",
            "The validated archive still requires source-gap, corporate-action, and point-in-time review.",
            "Overlapping forward-return samples are not independent trades.",
            "This is not the production BUY/SELL classifier and does not estimate live trading performance.",
            "No transaction costs, slippage, liquidity, or dividend treatment is included.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Normalized CSV or CSV.GZ archive")
    parser.add_argument("--output", required=True, type=Path, help="Path for JSON report")
    args = parser.parse_args()
    bars, summary = read_bars(args.input)
    report = analyze_bars(bars, summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "completed",
        "usable_rows": summary["usable_rows"],
        "symbols": summary["unique_symbols"],
        "pooled_forward_returns": report["pooled_forward_returns"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
