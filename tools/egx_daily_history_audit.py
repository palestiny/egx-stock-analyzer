#!/usr/bin/env python3
"""Read-only structural and quality audit for the canonical EGX daily-history CSV.

The audit never edits source data, repairs prices, infers missing sessions, or
claims that provider-reported values have been independently authenticated.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

EXPECTED_COLUMNS = (
    "session_date", "instrument_type", "symbol", "price_unit",
    "open_value", "high_value", "low_value", "close_value",
    "volume_thousands_reported", "change_pct_reported", "traded_value_egp",
    "executions_count", "source_name", "source_url", "retrieved_at",
    "price_type", "delay_status", "quality_status", "notes",
)
REQUIRED_NON_EMPTY = (
    "session_date", "instrument_type", "symbol", "price_unit",
    "open_value", "high_value", "low_value", "close_value",
    "change_pct_reported", "source_name", "source_url", "retrieved_at",
    "price_type", "delay_status", "quality_status", "notes",
)
NUMERIC_FIELDS = (
    "open_value", "high_value", "low_value", "close_value",
    "volume_thousands_reported", "change_pct_reported",
    "traded_value_egp", "executions_count",
)
QUALITY_STATUSES = {
    "source_reported",
    "reported_source_value",
    "ohlc_inconsistency_review",
    "source_conflict_review",
    "source_revision_conflict",
}
REVIEW_STATUSES = {
    "ohlc_inconsistency_review",
    "source_conflict_review",
    "source_revision_conflict",
}


def _decimal(value: str, field: str, row_number: int) -> Decimal | None:
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"row[{row_number}]:invalid_{field}={value!r}") from exc
    if not parsed.is_finite():
        raise ValueError(f"row[{row_number}]:non_finite_{field}={value!r}")
    return parsed


def _validate_retrieved_at(value: str, row_number: int) -> None:
    raw = value.strip()
    try:
        date.fromisoformat(raw)
        return
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"row[{row_number}]:invalid_retrieved_at={value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"row[{row_number}]:retrieved_at_timezone_missing")


def audit_csv_text(content: str, source_path: str = "<memory>") -> dict[str, object]:
    """Audit CSV text and return a deterministic report without changing it."""
    try:
        reader = csv.reader(io.StringIO(content, newline=""), strict=True)
        header = next(reader, None)
        if not header:
            raise ValueError("CSV has no header row")
        if len(header) != len(set(header)):
            raise ValueError("CSV contains duplicate headers")
        if tuple(header) != EXPECTED_COLUMNS:
            missing = [name for name in EXPECTED_COLUMNS if name not in header]
            unexpected = [name for name in header if name not in EXPECTED_COLUMNS]
            if missing or unexpected or len(header) != len(EXPECTED_COLUMNS):
                raise ValueError(
                    f"CSV schema mismatch; missing={missing}; unexpected={unexpected}"
                )
            raise ValueError("CSV columns are not in the canonical order")

        rows: list[tuple[int, dict[str, str]]] = []
        row_errors: list[dict[str, object]] = []
        for row_number, values in enumerate(reader, start=2):
            if not values:
                continue
            if len(values) != len(header):
                row_errors.append({
                    "row": row_number,
                    "reason": f"field_count_expected_{len(header)}_got_{len(values)}",
                })
                continue
            rows.append((row_number, dict(zip(header, values, strict=True))))
    except csv.Error as exc:
        raise ValueError("CSV contains malformed quoting or structure") from exc

    duplicate_counts: Counter[tuple[str, str]] = Counter()
    quality_counts: Counter[str] = Counter()
    missing_counts: Counter[str] = Counter()
    invalid_rows: list[dict[str, object]] = []
    ohlc_failures: list[dict[str, object]] = []
    unlabelled_ohlc_failures: list[dict[str, object]] = []
    review_rows: list[dict[str, str]] = []
    parsed_dates: list[date] = []
    symbols: set[str] = set()
    session_counts: Counter[str] = Counter()

    for row_number, row in rows:
        symbol = row["symbol"].strip().upper()
        session = row["session_date"].strip()
        quality = row["quality_status"].strip()
        if symbol:
            symbols.add(symbol)
            duplicate_counts[(session, symbol)] += 1
            session_counts[session] += 1
        if quality:
            quality_counts[quality] += 1

        row_problems: list[str] = []
        for field in REQUIRED_NON_EMPTY:
            if not row[field].strip():
                missing_counts[field] += 1
                row_problems.append(f"missing_{field}")
        for field in ("volume_thousands_reported", "traded_value_egp", "executions_count"):
            if not row[field].strip():
                missing_counts[field] += 1

        try:
            parsed_date = date.fromisoformat(session)
            parsed_dates.append(parsed_date)
        except ValueError:
            row_problems.append("invalid_session_date")

        if row["instrument_type"] not in {"equity", "index"}:
            row_problems.append("invalid_instrument_type")
        expected_unit = {"equity": "EGP", "index": "points"}.get(row["instrument_type"])
        if expected_unit and row["price_unit"] != expected_unit:
            row_problems.append("instrument_price_unit_mismatch")
        if not symbol:
            row_problems.append("empty_symbol")

        source_url = urlparse(row["source_url"].strip())
        if source_url.scheme not in {"http", "https"} or not source_url.netloc:
            row_problems.append("invalid_source_url")
        if row["quality_status"] and quality not in QUALITY_STATUSES:
            row_problems.append("unknown_quality_status")
        if row["retrieved_at"].strip():
            try:
                _validate_retrieved_at(row["retrieved_at"], row_number)
            except ValueError as exc:
                row_problems.append(str(exc).split(":", 1)[-1])

        values: dict[str, Decimal | None] = {}
        for field in NUMERIC_FIELDS:
            try:
                values[field] = _decimal(row[field], field, row_number)
            except ValueError as exc:
                row_problems.append(str(exc).split(":", 1)[-1])
                values[field] = None

        for field in ("open_value", "high_value", "low_value", "close_value"):
            value = values[field]
            if value is not None and value <= 0:
                row_problems.append(f"non_positive_{field}")
        for field in ("volume_thousands_reported", "traded_value_egp", "executions_count"):
            value = values[field]
            if value is not None and value < 0:
                row_problems.append(f"negative_{field}")

        o, h, low, close = (
            values["open_value"], values["high_value"],
            values["low_value"], values["close_value"],
        )
        if all(value is not None and value > 0 for value in (o, h, low, close)):
            assert o is not None and h is not None and low is not None and close is not None
            if not (low <= o <= h and low <= close <= h and low <= h):
                issue = {
                    "row": row_number,
                    "session_date": session,
                    "symbol": symbol,
                    "open": str(o),
                    "high": str(h),
                    "low": str(low),
                    "close": str(close),
                    "quality_status": quality,
                }
                ohlc_failures.append(issue)
                if quality not in REVIEW_STATUSES:
                    unlabelled_ohlc_failures.append(issue)

        if quality in REVIEW_STATUSES:
            review_rows.append({
                "session_date": session,
                "symbol": symbol,
                "quality_status": quality,
            })
        if row_problems:
            invalid_rows.append({
                "row": row_number,
                "session_date": session,
                "symbol": symbol,
                "issues": sorted(set(row_problems)),
            })

    duplicates = [
        {"session_date": key[0], "symbol": key[1], "count": count}
        for key, count in sorted(duplicate_counts.items()) if count > 1
    ]
    duplicate_extra_rows = sum(item["count"] - 1 for item in duplicates)
    sorted_dates = sorted(parsed_dates)
    latest_date = sorted_dates[-1].isoformat() if sorted_dates else None
    latest_session_rows = session_counts[latest_date] if latest_date else 0

    findings_count = (
        len(row_errors) + len(invalid_rows) + len(duplicates)
        + len(ohlc_failures) + len(review_rows)
    )
    return {
        "schema_version": 1,
        "audit": "egx_canonical_daily_history_csv",
        "status": "completed_with_findings" if findings_count else "clean",
        "input": source_path,
        "row_count": len(rows) + len(row_errors),
        "parsed_row_count": len(rows),
        "symbol_count": len(symbols),
        "session_count": len(set(parsed_dates)),
        "first_session_date": min(parsed_dates).isoformat() if parsed_dates else None,
        "last_session_date": latest_date,
        "latest_session_row_count": latest_session_rows,
        "latest_session_symbols": sorted({
            row["symbol"].strip().upper() for _, row in rows
            if latest_date and row["session_date"].strip() == latest_date
        }),
        "quality_status_counts": dict(sorted(quality_counts.items())),
        "missing_value_counts": dict(sorted(missing_counts.items())),
        "duplicate_keys": duplicates,
        "duplicate_extra_rows": duplicate_extra_rows,
        "invalid_row_count": len(invalid_rows),
        "invalid_rows": invalid_rows,
        "ohlc_inconsistency_count": len(ohlc_failures),
        "ohlc_inconsistencies": ohlc_failures,
        "unlabelled_ohlc_inconsistency_count": len(unlabelled_ohlc_failures),
        "review_row_count": len(review_rows),
        "review_rows": review_rows,
        "malformed_row_count": len(row_errors),
        "malformed_rows": row_errors,
        "source_authenticity": "NOT_INDEPENDENTLY_VERIFIED",
        "limitations": [
            "This is a structural and arithmetic audit of the supplied CSV only.",
            "Source URLs and retrieval metadata are checked for shape, not authenticity.",
            "No EGX trading calendar, missing session, or missing instrument is inferred.",
            "Blank volume, traded value, and execution counts remain unavailable, not zero.",
            "Provider-reported values are never repaired or replaced.",
            "Rows with review quality statuses or OHLC inconsistencies must be excluded from clean OHLC analysis until reconciled.",
        ],
    }


def audit_file(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 or UTF-8 with BOM") from exc
    report = audit_csv_text(content, str(path))
    report["artifact"] = {
        "filename": path.name,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Canonical EGX daily-history CSV")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    report = audit_file(args.input)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 1 if report["status"] != "clean" else 0


if __name__ == "__main__":
    raise SystemExit(main())
