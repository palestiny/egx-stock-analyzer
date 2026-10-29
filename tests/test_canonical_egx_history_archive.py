"""Offline integrity checks for the version-controlled EGX daily-history seed."""

import csv
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_PATH = REPOSITORY_ROOT / "data" / "market_history" / "egx_daily_history.csv"
README_PATH = REPOSITORY_ROOT / "data" / "market_history" / "README.md"

EXPECTED_FIELDS = (
    "session_date",
    "symbol",
    "open_egp",
    "high_egp",
    "low_egp",
    "close_egp",
    "volume_thousands_reported",
    "change_pct_reported",
    "traded_value_egp",
    "executions_count",
    "source_name",
    "source_url",
    "retrieved_at",
    "price_type",
    "delay_status",
    "quality_status",
    "notes",
)

PRICE_FIELDS = ("open_egp", "high_egp", "low_egp", "close_egp")
OPTIONAL_NON_NEGATIVE_FIELDS = ("traded_value_egp", "executions_count")


def _read_archive() -> list[dict[str, str]]:
    with ARCHIVE_PATH.open(encoding="utf-8", newline="") as archive_file:
        reader = csv.DictReader(archive_file)
        assert tuple(reader.fieldnames or ()) == EXPECTED_FIELDS
        rows = list(reader)

    assert rows, "The canonical EGX history archive must not be empty."
    for row in rows:
        assert set(row) == set(EXPECTED_FIELDS), (
            "Each CSV record must have exactly the declared fields."
        )
    return rows


def _decimal(row: dict[str, str], field: str) -> Decimal:
    try:
        value = Decimal(row[field])
    except (InvalidOperation, KeyError, TypeError) as error:
        raise AssertionError(f"{field} must contain a valid decimal.") from error

    assert value.is_finite(), f"{field} must be finite."
    return value


def test_canonical_archive_has_rows_and_unique_session_symbol_keys():
    rows = _read_archive()
    seen_keys: set[tuple[date, str]] = set()

    for row in rows:
        session_date = date.fromisoformat(row["session_date"])
        assert session_date.isoformat() == row["session_date"]

        symbol = row["symbol"]
        assert re.fullmatch(r"[A-Z0-9][A-Z0-9.-]*", symbol), (
            f"Invalid normalized ticker symbol: {symbol!r}"
        )

        key = (session_date, symbol)
        assert key not in seen_keys, f"Duplicate session/symbol key: {key}"
        seen_keys.add(key)

        retrieved_at = date.fromisoformat(row["retrieved_at"])
        assert retrieved_at.isoformat() == row["retrieved_at"]
        assert session_date <= retrieved_at


def test_ohlc_values_are_finite_positive_and_internally_consistent():
    for row in _read_archive():
        prices = {field: _decimal(row, field) for field in PRICE_FIELDS}
        assert all(value > 0 for value in prices.values())

        assert prices["high_egp"] >= max(
            prices["open_egp"], prices["low_egp"], prices["close_egp"]
        ), f"High does not bound OHLC values for {row['symbol']} on {row['session_date']}"
        assert prices["low_egp"] <= min(
            prices["open_egp"], prices["high_egp"], prices["close_egp"]
        ), f"Low does not bound OHLC values for {row['symbol']} on {row['session_date']}"


def test_reported_volume_changes_and_optional_values_are_numeric():
    for row in _read_archive():
        assert _decimal(row, "volume_thousands_reported") >= 0
        _decimal(row, "change_pct_reported")

        for field in OPTIONAL_NON_NEGATIVE_FIELDS:
            if row[field].strip():
                value = _decimal(row, field)
                assert value >= 0, f"{field} cannot be negative."
                if field == "executions_count":
                    assert value == value.to_integral_value(), (
                        "executions_count must be a whole number."
                    )


def test_each_record_keeps_source_provenance_and_quality_labels():
    for row in _read_archive():
        assert row["source_name"].strip()
        assert row["source_url"].strip()
        parsed_url = urlparse(row["source_url"])
        assert parsed_url.scheme == "https"
        assert parsed_url.netloc

        for field in ("price_type", "delay_status", "quality_status", "notes"):
            assert row[field].strip(), f"{field} must explain data semantics."


def test_archive_documentation_preserves_known_data_limitations():
    documentation = README_PATH.read_text(encoding="utf-8")
    assert "not an exact share count" in documentation
    assert "Cross-source reconciliation remains pending" in documentation
    assert "not accepted as a production feed" in documentation
