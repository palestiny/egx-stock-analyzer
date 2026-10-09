"""Pure validation helpers for M61 market-source acquisition responses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal, InvalidOperation


REQUIRED_FIELDS = ("date", "open", "high", "low", "close", "volume")


def validate_history_points(points: Sequence[Mapping[str, object]]) -> list[str]:
    """Return deterministic findings without assuming an exchange calendar."""
    findings: list[str] = []
    previous_date: date | None = None
    seen_dates: set[str] = set()

    for index, point in enumerate(points):
        raw_date = point.get("date")
        current_date: date | None = None
        if "date" not in point:
            findings.append(f"row[{index}]:missing=date")
        else:
            try:
                current_date = date.fromisoformat(str(raw_date))
            except ValueError:
                findings.append(f"row[{index}]:invalid_date={raw_date}")

            if current_date is not None:
                date_key = current_date.isoformat()
                if date_key in seen_dates:
                    findings.append(f"row[{index}]:duplicate_date={date_key}")
                seen_dates.add(date_key)
                if previous_date is not None and current_date < previous_date:
                    findings.append(f"row[{index}]:out_of_order={date_key}")
                previous_date = current_date

        missing = [field for field in REQUIRED_FIELDS if field not in point and field != "date"]
        if missing:
            findings.append(f"row[{index}]:missing={','.join(missing)}")
            continue

        if current_date is None:
            continue

        values: dict[str, Decimal] = {}
        for field in ("open", "high", "low", "close", "volume"):
            try:
                value = Decimal(str(point[field]))
            except (TypeError, ValueError, InvalidOperation):
                findings.append(f"row[{index}]:invalid_{field}={point[field]}")
                continue
            if not value.is_finite():
                findings.append(f"row[{index}]:non_finite_{field}={point[field]}")
                continue
            if field in {"open", "high", "low", "close"} and value <= 0:
                findings.append(f"row[{index}]:non_positive_{field}={point[field]}")
            values[field] = value

        if all(field in values for field in ("open", "high", "low", "close")):
            if values["low"] > values["high"]:
                findings.append(f"row[{index}]:low_above_high")
            if values["low"] > values["open"] or values["low"] > values["close"]:
                findings.append(f"row[{index}]:low_above_ohlc")
            if values["high"] < values["open"] or values["high"] < values["close"]:
                findings.append(f"row[{index}]:high_below_ohlc")

        if "volume" in values and values["volume"] < 0:
            findings.append(f"row[{index}]:negative_volume")

    return findings


def validate_m61_evaluation_window(points: Sequence[Mapping[str, object]]) -> list[str]:
    """Validate the bounded M61 evaluation window and its 252-observation warm-up.

    This intentionally does not infer an EGX trading calendar. It validates only
    evidence present in the provider response: dates before the evaluation start,
    evaluation-window coverage, and deterministic ordering/uniqueness.
    """
    findings: list[str] = []
    parsed_dates: list[date] = []

    for point in points:
        try:
            parsed_dates.append(date.fromisoformat(str(point.get("date"))))
        except (TypeError, ValueError):
            continue

    if not parsed_dates:
        return ["m61:no_valid_dates"]

    evaluation_start = date(2021, 1, 1)
    evaluation_end = date(2025, 12, 31)
    # Count distinct sessions, not rows: duplicate observations must never inflate
    # warm-up or evaluation coverage even though they are also reported separately.
    unique_dates = sorted(set(parsed_dates))
    warmup_count = sum(item < evaluation_start for item in unique_dates)
    evaluation_count = sum(evaluation_start <= item <= evaluation_end for item in unique_dates)

    if warmup_count < 252:
        findings.append(f"m61:insufficient_warmup={warmup_count};required=252")
    if evaluation_count == 0:
        findings.append("m61:no_evaluation_window_rows")
    if min(unique_dates) > date(2020, 1, 1):
        findings.append(f"m61:coverage_starts_after_requested={min(unique_dates).isoformat()}")
    if max(unique_dates) < evaluation_end:
        findings.append(f"m61:coverage_ends_before_evaluation_end={max(unique_dates).isoformat()}")

    return findings
