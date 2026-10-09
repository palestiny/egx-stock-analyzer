#!/usr/bin/env python3
"""No-cost Yahoo chart endpoint probe for M61 market-data exploration.

This is diagnostic acquisition tooling, not an accepted data source or production
provider. It preserves the exact response bytes only when explicitly requested.
Provider terms and retention/use rights must be reviewed independently.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tools.m61_market_validation import (
    validate_history_points,
    validate_m61_evaluation_window,
)

COHORT: dict[str, str] = {
    "COMI": "COMI.CA",
    "EGAL": "EGAL.CA",
    "SWDY": "SWDY.CA",
    "ETEL": "ETEL.CA",
    "EAST": "EAST.CA",
    "TMGH": "TMGH.CA",
    "PHDC": "PHDC.CA",
    "FWRY": "FWRY.CA",
    "EFID": "EFID.CA",
    "HRHO": "HRHO.CA",
}
FROM_DATE = date(2019, 1, 1)
END_EXCLUSIVE = date(2026, 1, 1)
BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"


def build_url(ticker: str) -> str:
    """Build the fixed, bounded daily-history request for a known ticker."""
    if ticker not in COHORT.values():
        raise ValueError("ticker is not in the fixed M61 exploratory cohort")
    start = int(datetime.combine(FROM_DATE, datetime.min.time(), tzinfo=UTC).timestamp())
    end = int(datetime.combine(END_EXCLUSIVE, datetime.min.time(), tzinfo=UTC).timestamp())
    query = urllib.parse.urlencode(
        {
            "period1": str(start),
            "period2": str(end),
            "interval": "1d",
            "events": "div,splits",
            "includeAdjustedClose": "true",
        }
    )
    return f"{BASE_URL}/{urllib.parse.quote(ticker, safe='')}?{query}"


def request_chart(ticker: str) -> tuple[int, object, bytes]:
    """Request one public chart response, retaining the exact response bytes."""
    request = urllib.request.Request(
        build_url(ticker),
        headers={
            "Accept": "application/json",
            "User-Agent": "egx-stock-analyzer-m61-free-probe/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read()
            try:
                payload: object = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                payload = {"error": "invalid_json_response"}
            return response.status, payload, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {"error": "http_error_response_not_json"}
        return exc.code, payload, raw
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        kind = "request_timeout" if isinstance(exc, TimeoutError) else "request_failed"
        return 0, {"error": kind, "error_type": type(exc).__name__}, b""


def _finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def _parse_chart(ticker: str, payload: object) -> tuple[list[dict[str, object]], dict[str, object], list[str]]:
    findings: list[str] = []
    meta_out: dict[str, object] = {}
    if not isinstance(payload, dict):
        return [], meta_out, ["response:not_object"]

    chart = payload.get("chart")
    if not isinstance(chart, dict):
        return [], meta_out, ["response:chart_not_object"]
    error = chart.get("error")
    if error:
        return [], meta_out, [f"response:provider_error={str(error)[:240]}"]
    results = chart.get("result")
    if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
        return [], meta_out, ["response:expected_exactly_one_chart_result"]

    result = results[0]
    meta = result.get("meta")
    if not isinstance(meta, dict):
        return [], meta_out, ["response:meta_not_object"]

    actual_ticker = meta.get("symbol")
    if not isinstance(actual_ticker, str) or actual_ticker.upper() != ticker.upper():
        findings.append(f"response:ticker_mismatch={actual_ticker!r}")
        return [], {"ticker": actual_ticker}, findings
    exchange_timezone = meta.get("exchangeTimezoneName")
    if not isinstance(exchange_timezone, str) or not exchange_timezone.strip():
        findings.append("response:missing_exchange_timezone")
        return [], {"ticker": actual_ticker, "exchange_timezone": exchange_timezone}, findings
    if exchange_timezone != "Africa/Cairo":
        findings.append(f"response:unexpected_exchange_timezone={exchange_timezone!r}")
        return [], {"ticker": actual_ticker, "exchange_timezone": exchange_timezone}, findings
    currency = meta.get("currency")
    if currency != "EGP":
        findings.append(f"response:unexpected_currency={currency!r}")
        return [], {"ticker": actual_ticker, "exchange_timezone": exchange_timezone, "currency": currency}, findings
    try:
        session_timezone = ZoneInfo(exchange_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        findings.append(f"response:unknown_exchange_timezone={exchange_timezone!r}")
        return [], {"ticker": actual_ticker, "exchange_timezone": exchange_timezone}, findings

    timestamps = result.get("timestamp")
    indicators = result.get("indicators")
    if not isinstance(timestamps, list) or not isinstance(indicators, dict):
        findings.append("response:missing_timestamps_or_indicators")
        return [], {"ticker": actual_ticker, "exchange_timezone": exchange_timezone}, findings
    quote_rows = indicators.get("quote")
    if not isinstance(quote_rows, list) or len(quote_rows) != 1 or not isinstance(quote_rows[0], dict):
        findings.append("response:quote_not_single_object")
        return [], {"ticker": actual_ticker, "exchange_timezone": exchange_timezone}, findings
    quote = quote_rows[0]
    arrays: dict[str, list[object]] = {}
    for field in ("open", "high", "low", "close", "volume"):
        values = quote.get(field)
        if not isinstance(values, list) or len(values) != len(timestamps):
            findings.append(f"response:invalid_array={field}")
            return [], {"ticker": actual_ticker, "exchange_timezone": exchange_timezone}, findings
        arrays[field] = values

    adj_close_values: list[object] = []
    adj_rows = indicators.get("adjclose")
    if isinstance(adj_rows, list) and len(adj_rows) == 1 and isinstance(adj_rows[0], dict):
        raw_adj = adj_rows[0].get("adjclose")
        if isinstance(raw_adj, list) and len(raw_adj) == len(timestamps):
            adj_close_values = raw_adj
    if not adj_close_values:
        findings.append("response:adjusted_close_unavailable")

    events = result.get("events")
    events = events if isinstance(events, dict) else {}
    dividends = events.get("dividends")
    dividends = dividends if isinstance(dividends, dict) else {}
    splits = events.get("splits")
    splits = splits if isinstance(splits, dict) else {}

    dividend_by_date: dict[str, object] = {}
    for event in dividends.values():
        if isinstance(event, dict) and isinstance(event.get("date"), int):
            event_day = datetime.fromtimestamp(event["date"], UTC).astimezone(session_timezone).date().isoformat()
            dividend_by_date[event_day] = event.get("amount")
    split_by_date: dict[str, object] = {}
    for event in splits.values():
        if isinstance(event, dict) and isinstance(event.get("date"), int):
            event_day = datetime.fromtimestamp(event["date"], UTC).astimezone(session_timezone).date().isoformat()
            split_by_date[event_day] = event.get("numerator")

    points: list[dict[str, object]] = []
    for index, timestamp in enumerate(timestamps):
        if (
            isinstance(timestamp, bool)
            or not isinstance(timestamp, (int, float))
            or not math.isfinite(timestamp)
        ):
            findings.append(f"row[{index}]:invalid_timestamp")
            continue
        try:
            session_date = datetime.fromtimestamp(timestamp, UTC).astimezone(session_timezone).date()
        except (OverflowError, OSError, ValueError):
            findings.append(f"row[{index}]:timestamp_out_of_range")
            continue
        if not FROM_DATE <= session_date < END_EXCLUSIVE:
            findings.append(f"row[{index}]:date_outside_requested_range={session_date.isoformat()}")
            continue
        session_day = session_date.isoformat()
        row: dict[str, object] = {
            "date": session_day,
            "open": arrays["open"][index],
            "high": arrays["high"][index],
            "low": arrays["low"][index],
            "close": arrays["close"][index],
            "volume": arrays["volume"][index],
        }
        for field in ("open", "high", "low", "close", "volume"):
            value = row[field]
            if value is None:
                findings.append(f"row[{index}]:null={field}")
            elif not _finite_number(value):
                findings.append(f"row[{index}]:invalid_{field}={value!r}")
        if index < len(adj_close_values):
            row["adj_close"] = adj_close_values[index]
        row["dividend"] = dividend_by_date.get(session_day)
        row["split_numerator"] = split_by_date.get(session_day)
        points.append(row)

    meta_out = {
        "ticker": actual_ticker,
        "exchange_timezone": exchange_timezone,
        "currency": meta.get("currency"),
        "exchange_name": meta.get("fullExchangeName"),
        "instrument_type": meta.get("instrumentType"),
        "price_hint": meta.get("priceHint"),
    }
    return points, meta_out, findings


def probe_ticker(symbol: str, ticker: str, preserve_raw: bool, output_dir: Path) -> dict[str, Any]:
    status_code, payload, raw = request_chart(ticker)
    points, meta, parse_findings = _parse_chart(ticker, payload)
    validation_findings = validate_history_points(points)
    evaluation_findings = validate_m61_evaluation_window(points)
    findings = list(dict.fromkeys(parse_findings + validation_findings + evaluation_findings))

    report: dict[str, Any] = {
        "symbol": symbol,
        "source": "Yahoo Finance chart endpoint",
        "ticker": ticker,
        "status_code": status_code,
        "requested": {
            "from": FROM_DATE.isoformat(),
            "to_exclusive": END_EXCLUSIVE.isoformat(),
            "interval": "1d",
            "adjusted_close_preserved_separately": True,
            "corporate_action_events_requested": True,
        },
        "observed": {
            **meta,
            "row_count": len(points),
            "first_date": points[0]["date"] if points else None,
            "last_date": points[-1]["date"] if points else None,
            "sha256_of_response": hashlib.sha256(raw).hexdigest() if raw else None,
            "response_bytes": len(raw),
            "validation_findings": findings,
            "corporate_action_event_rows": sum(
                1 for point in points if point.get("dividend") is not None or point.get("split_numerator") is not None
            ),
        },
        "acceptance": {
            "status": "CANDIDATE_ONLY",
            "source_terms_verified": False,
            "long_term_storage_rights_verified": False,
            "point_in_time_financials_included": False,
            "eligible_for_strategy_v0": False,
        },
    }

    if preserve_raw and raw:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{symbol}.yahoo-chart.raw.json").write_bytes(raw)
        with (output_dir / f"{symbol}.market-candidate.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=(
                    "symbol", "source_ticker", "date", "open", "high", "low", "close",
                    "volume", "adj_close", "dividend", "split_numerator", "source_timezone",
                ),
            )
            writer.writeheader()
            for point in points:
                writer.writerow(
                    {
                        "symbol": symbol,
                        "source_ticker": ticker,
                        **point,
                        "source_timezone": meta.get("exchange_timezone"),
                    }
                )
        report["observed"]["raw_artifact"] = f"{symbol}.yahoo-chart.raw.json"
        report["observed"]["candidate_csv"] = f"{symbol}.market-candidate.csv"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--symbols",
        nargs="+",
        choices=tuple(COHORT),
        default=list(COHORT),
        help="Subset of the fixed M61 cohort; defaults to all ten symbols.",
    )
    parser.add_argument(
        "--preserve-raw",
        action="store_true",
        help="Explicitly save exact provider responses and candidate CSVs locally.",
    )
    args = parser.parse_args(argv)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("output directory must be absent or empty; refusing to overwrite evidence")

    reports = [
        probe_ticker(symbol, COHORT[symbol], args.preserve_raw, args.output_dir)
        for symbol in args.symbols
    ]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_report = {
        "status": "CANDIDATE_ONLY",
        "source": "Yahoo Finance chart endpoint",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "cohort": args.symbols,
        "paid_access_required_by_this_tool": False,
        "legal_use_or_redistribution_verified": False,
        "point_in_time_financial_data_included": False,
        "eligible_for_strategy_v0": False,
        "symbols": reports,
    }
    report_path = args.output_dir / "free-market-probe-report.json"
    report_path.write_text(json.dumps(run_report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "status": "CANDIDATE_ONLY", "symbols": len(reports)}))
    return 0 if any(item["status_code"] == 200 for item in reports) else 2


if __name__ == "__main__":
    raise SystemExit(main())
