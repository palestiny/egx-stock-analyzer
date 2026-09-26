"""Pure validation helpers for M61 market-source acquisition responses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from math import isfinite


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

        values: dict[str, float] = {}
        for field in ("open", "high", "low", "close", "volume"):
            try:
                value = float(point[field])
            except (TypeError, ValueError):
                findings.append(f"row[{index}]:invalid_{field}={point[field]}")
                continue
            if not isfinite(value):
                findings.append(f"row[{index}]:non_finite_{field}={point[field]}")
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
