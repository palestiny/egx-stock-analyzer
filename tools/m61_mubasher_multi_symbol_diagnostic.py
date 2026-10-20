"""Cross-symbol momentum/volume forward-return diagnostic using public Mubasher CSVs.

Workflow trigger revision: 2026-10-20. The source URLs are public references, not
a guarantee that each CSV remains accessible or retains the expected schema.

This is a research-only, network-dependent tool. It does not feed production
recommendations and does not replace the accepted M61 dataset gate.
"""
from __future__ import annotations

import csv
import json
import urllib.request
from datetime import date
from collections import defaultdict
from decimal import Decimal
from statistics import median
from typing import Any

SOURCES = {
    "COMI": ("https://english.mubasher.info/markets/EGX/stocks/COMI", "https://static.mubasher.info/File.MubasherCharts/File.Historical_Stock_Charts_Dir/44507230b2b03e2da37352abf1a659545b44.csv"),
    "EGAL": ("https://english.mubasher.info/markets/EGX/stocks/EGAL", "https://static.mubasher.info/File.MubasherCharts/File.Historical_Stock_Charts_Dir/259218bb68e2b38e4a8ce7cf4f6b2625768c.csv"),
    "ABUK": ("https://english.mubasher.info/markets/EGX/stocks/ABUK", "https://static.mubasher.info/File.MubasherCharts/File.Historical_Stock_Charts_Dir/112969a5b5995110b36a9a347898d97a610e.csv"),
    "TMGH": ("https://english.mubasher.info/markets/EGX/stocks/TMGH", "https://static.mubasher.info/File.MubasherCharts/File.Historical_Stock_Charts_Dir/4484803ef56843860e4a48fc4cdb3065e8ce.csv"),
    "EAST": ("https://english.mubasher.info/markets/EGX/stocks/EAST", "https://static.mubasher.info/File.MubasherCharts/File.Historical_Stock_Charts_Dir/296460ad83801910ec976590f69f638e0d6d.csv"),
    "FWRY": ("https://english.mubasher.info/markets/EGX/stocks/FWRY", "https://static.mubasher.info/File.MubasherCharts/File.Historical_Stock_Charts_Dir/13975494d8dbca2d30897065e5de7e2dbb0fd56.csv"),
    "ETEL": ("https://english.mubasher.info/markets/EGX/stocks/ETEL", "https://static.mubasher.info/File.MubasherCharts/File.Historical_Stock_Charts_Dir/4470a3ab4ff8fa4deed2e3bae3a5077675f0.csv"),
    "EFIH": ("https://english.mubasher.info/markets/EGX/stocks/EFIH", "https://static.mubasher.info/File.MubasherCharts/File.Historical_Stock_Charts_Dir/13979726390f435ae7002c4a63ee00f45eca439.csv"),
    "HRHO": ("https://english.mubasher.info/markets/EGX/stocks/HRHO", "https://static.mubasher.info/File.MubasherCharts/File.Historical_Stock_Charts_Dir/446888c040adb393832c87914347cc2afc3f.csv"),
    "ADIB": ("https://english.mubasher.info/markets/EGX/stocks/ADIB", "https://static.mubasher.info/File.MubasherCharts/File.Historical_Stock_Charts_Dir/1386439a399a8a7dacebc9a8f3fd1de08e57391.csv"),
}
HORIZONS = (1, 3, 5, 10)
LOOKBACK = 5
VOLUME_MULTIPLE = Decimal("1.5")


def _fetch_rows(symbol: str, page_url: str, csv_url: str) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        csv_url,
        headers={
            "User-Agent": "EGX-Stock-Analyzer research diagnostic",
            "Referer": page_url,
            "Accept": "text/csv,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8-sig")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    rejected = 0
    for line in csv.reader(body.splitlines()):
        if len(line) < 6:
            rejected += 1
            continue
        session = line[0].split("/", 1)[0].strip()
        try:
            if len(session) != 10 or session[4] != "-" or session[7] != "-":
                raise ValueError("invalid ISO date")
            date.fromisoformat(session)
            opening, high, low, close = (Decimal(v.strip()) for v in line[1:5])
            volume = Decimal(line[5].strip())
            if min(opening, high, low, close) <= 0 or volume < 0:
                raise ValueError("non-positive OHLC or negative volume")
            if high < max(opening, close) or low > min(opening, close) or high < low:
                raise ValueError("invalid OHLC relationships")
            if session in seen:
                rejected += 1
                continue
            seen.add(session)
            rows.append({"date": session, "open": opening, "high": high, "low": low, "close": close, "volume": volume})
        except (ValueError, ArithmeticError):
            rejected += 1
    rows.sort(key=lambda row: row["date"])
    if len(rows) < 30:
        raise ValueError(f"{symbol}: only {len(rows)} valid rows after parsing; rejected={rejected}")
    return rows


def _stats(values: list[Decimal]) -> dict[str, Any]:
    if not values:
        return {"samples": 0, "mean_return": None, "median_return": None, "win_rate": None, "worst_return": None}
    return {
        "samples": len(values),
        "mean_return": str(sum(values, Decimal(0)) / len(values)),
        "median_return": str(Decimal(str(median(values)))),
        "win_rate": str(Decimal(sum(v > 0 for v in values)) / len(values)),
        "worst_return": str(min(values)),
    }


def _evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[int]] = {
        "all_eligible_sessions": [],
        "positive_momentum": [],
        "positive_momentum_and_volume_at_least_1_5x": [],
    }
    for i in range(LOOKBACK, len(rows) - 1):
        prior_close = rows[i - LOOKBACK]["close"]
        if prior_close <= 0:
            continue
        groups["all_eligible_sessions"].append(i)
        if rows[i]["close"] > prior_close:
            groups["positive_momentum"].append(i)
            previous_volumes = [r["volume"] for r in rows[i - LOOKBACK:i]]
            average_volume = sum(previous_volumes, Decimal(0)) / LOOKBACK
            if average_volume > 0 and rows[i]["volume"] / average_volume >= VOLUME_MULTIPLE:
                groups["positive_momentum_and_volume_at_least_1_5x"].append(i)

    result: dict[str, Any] = {}
    for name, indexes in groups.items():
        by_horizon: dict[str, Any] = {}
        for horizon in HORIZONS:
            returns: list[Decimal] = []
            for i in indexes:
                exit_index = i + horizon
                if exit_index >= len(rows):
                    continue
                entry = rows[i + 1]["open"]
                exit_close = rows[exit_index]["close"]
                if entry > 0:
                    returns.append((exit_close - entry) / entry)
            by_horizon[str(horizon)] = _stats(returns)
        result[name] = by_horizon
    return result


def run() -> dict[str, Any]:
    symbols: dict[str, Any] = {}
    failures: dict[str, str] = {}
    for symbol, (page_url, csv_url) in SOURCES.items():
        try:
            rows = _fetch_rows(symbol, page_url, csv_url)
            symbols[symbol] = {"rows": rows, "page_url": page_url, "csv_url": csv_url}
        except Exception as exc:  # per-symbol isolation; report failures explicitly
            failures[symbol] = f"{type(exc).__name__}: {exc}"

    if len(symbols) < 3:
        return {
            "diagnostic": "Mubasher multi-symbol momentum and volume forward returns",
            "status": "insufficient_source_data",
            "symbols_retrieved": sorted(symbols),
            "failures": failures,
            "limitations": [
                "Fewer than three symbols had at least 30 parseable rows.",
                "No pooled returns were calculated.",
                "Public aggregator data and licensing are not independently verified.",
            ],
        }

    common_start = max(data["rows"][0]["date"] for data in symbols.values())
    common_end = min(data["rows"][-1]["date"] for data in symbols.values())
    if common_start >= common_end:
        return {
            "diagnostic": "Mubasher multi-symbol momentum and volume forward returns",
            "status": "no_common_window",
            "symbols_retrieved": sorted(symbols),
            "failures": failures,
            "available_ranges": {
                symbol: {"start": data["rows"][0]["date"], "end": data["rows"][-1]["date"]}
                for symbol, data in symbols.items()
            },
        }
    per_symbol: dict[str, Any] = {}
    for symbol, data in symbols.items():
        rows = [row for row in data["rows"] if common_start <= row["date"] <= common_end]
        if len(rows) < 30:
            failures[symbol] = f"Only {len(rows)} rows in common window {common_start}..{common_end}"
            continue
        per_symbol[symbol] = {
            "rows": len(rows),
            "start": rows[0]["date"],
            "end": rows[-1]["date"],
            "signals": _evaluate(rows),
        }
    if len(per_symbol) < 3:
        return {
            "diagnostic": "Mubasher multi-symbol momentum and volume forward returns",
            "status": "insufficient_common_window_data",
            "common_window": {"start": common_start, "end": common_end},
            "symbols": per_symbol,
            "failures": failures,
            "limitations": ["Fewer than three symbols had 30 rows in the common window."],
        }

    # Pool raw observations across symbols; each symbol contributes each eligible signal.
    pooled: dict[str, dict[str, list[Decimal]]] = defaultdict(lambda: defaultdict(list))
    for symbol, data in symbols.items():
        if symbol not in per_symbol:
            continue
        rows = [row for row in data["rows"] if common_start <= row["date"] <= common_end]
        groups: dict[str, list[int]] = {
            "all_eligible_sessions": [],
            "positive_momentum": [],
            "positive_momentum_and_volume_at_least_1_5x": [],
        }
        for i in range(LOOKBACK, len(rows) - 1):
            groups["all_eligible_sessions"].append(i)
            if rows[i]["close"] > rows[i - LOOKBACK]["close"]:
                groups["positive_momentum"].append(i)
                avg = sum((r["volume"] for r in rows[i - LOOKBACK:i]), Decimal(0)) / LOOKBACK
                if avg > 0 and rows[i]["volume"] / avg >= VOLUME_MULTIPLE:
                    groups["positive_momentum_and_volume_at_least_1_5x"].append(i)
        for group, indexes in groups.items():
            for horizon in HORIZONS:
                for i in indexes:
                    exit_index = i + horizon
                    if exit_index >= len(rows):
                        continue
                    entry = rows[i + 1]["open"]
                    if entry > 0:
                        pooled[group][str(horizon)].append((rows[exit_index]["close"] - entry) / entry)

    return {
        "diagnostic": "Mubasher multi-symbol momentum and volume forward returns",
        "status": "completed",
        "source_registry": "AhmedYasserShalaby/egx-research-toolkit data/stock_rotation/universe.csv",
        "source_rights": "underlying market-data redistribution terms not independently verified; diagnostic use only",
        "execution_assumption": "signal after session close; enter next session open; exit at close after 1/3/5/10 sessions",
        "signal_definitions": {
            "positive_momentum": "close today > close five sessions earlier",
            "volume_confirmation": "positive momentum and current volume >= 1.5x mean volume of the five preceding sessions",
        },
        "common_window": {"start": common_start, "end": common_end},
        "symbols": per_symbol,
        "pooled_by_signal_group": {
            group: {horizon: _stats(values) for horizon, values in horizons.items()}
            for group, horizons in pooled.items()
        },
        "failures": failures,
        "limitations": [
            "public aggregator CSVs; source completeness, corporate actions and data licensing are not independently verified",
            "signals overlap and pooled observations are not independent",
            "returns are gross price returns and exclude costs, liquidity impact, and risk adjustment",
            "this is not the M61 ten-symbol 2021-2025 acceptance dataset or a recommendation",
        ],
    }


def main() -> None:
    report = run()
    print(json.dumps(report, indent=2, sort_keys=True))
    if report.get("status") != "completed":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
