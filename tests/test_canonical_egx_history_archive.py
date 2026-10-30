"""Offline integrity checks for the version-controlled EGX daily-history archive."""

import csv
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_PATH = REPOSITORY_ROOT / "data" / "market_history" / "egx_daily_history.csv"
README_PATH = REPOSITORY_ROOT / "data" / "market_history" / "README.md"

LEGACY_FIELDS = (
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

CANONICAL_FIELDS = (
    "session_date",
    "instrument_type",
    "symbol",
    "price_unit",
    "open_value",
    "high_value",
    "low_value",
    "close_value",
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

OPTIONAL_NON_NEGATIVE_FIELDS = (
    "volume_thousands_reported",
    "traded_value_egp",
    "executions_count",
)


def _read_archive() -> list[dict[str, str]]:
    with ARCHIVE_PATH.open(encoding="utf-8", newline="") as archive_file:
        reader = csv.DictReader(archive_file)
        fields = tuple(reader.fieldnames or ())
        assert fields in (LEGACY_FIELDS, CANONICAL_FIELDS), (
            "The canonical archive must use a declared legacy or instrument-aware schema."
        )
        rows = list(reader)

    assert rows, "The canonical EGX history archive must not be empty."
    for row in rows:
        assert set(row) == set(fields), (
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


def _retrieval_date(value: str) -> date:
    if "T" not in value:
        parsed_date = date.fromisoformat(value)
        assert parsed_date.isoformat() == value
        return parsed_date

    parsed_datetime = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed_datetime.tzinfo is not None, (
        "Timestamped retrieval provenance must include an explicit UTC offset."
    )
    assert parsed_datetime.utcoffset() is not None
    return parsed_datetime.date()


def _price_fields(row: dict[str, str]) -> tuple[str, str, str, str]:
    if "open_value" in row:
        return ("open_value", "high_value", "low_value", "close_value")
    return ("open_egp", "high_egp", "low_egp", "close_egp")


def test_canonical_archive_has_rows_and_unique_session_symbol_keys():
    rows = _read_archive()
    seen_keys: set[tuple[date, str]] = set()

    for row in rows:
        session_date = date.fromisoformat(row["session_date"])
        assert session_date.isoformat() == row["session_date"]

        symbol = row["symbol"]
        assert re.fullmatch(r"[A-Z0-9][A-Z0-9.-]*", symbol), (
            f"Invalid normalized instrument symbol: {symbol!r}"
        )

        key = (session_date, symbol)
        assert key not in seen_keys, f"Duplicate session/symbol key: {key}"
        seen_keys.add(key)

        assert session_date <= _retrieval_date(row["retrieved_at"])

        if "instrument_type" in row:
            assert row["instrument_type"] in {"equity", "index"}
            expected_unit = (
                "EGP" if row["instrument_type"] == "equity" else "points"
            )
            assert row["price_unit"] == expected_unit


def test_ohlc_values_are_positive_and_inconsistencies_are_explicitly_flagged():
    for row in _read_archive():
        open_field, high_field, low_field, close_field = _price_fields(row)
        prices = {
            "open": _decimal(row, open_field),
            "high": _decimal(row, high_field),
            "low": _decimal(row, low_field),
            "close": _decimal(row, close_field),
        }
        assert all(value > 0 for value in prices.values())

        is_consistent = (
            prices["high"] >= max(
                prices["open"], prices["low"], prices["close"]
            )
            and prices["low"] <= min(
                prices["open"], prices["high"], prices["close"]
            )
        )
        quality_status = row["quality_status"]
        if is_consistent:
            assert quality_status != "ohlc_inconsistency_review"
        else:
            assert quality_status == "ohlc_inconsistency_review", (
                f"Unflagged OHLC inconsistency for "
                f"{row['symbol']} on {row['session_date']}"
            )
            assert row["notes"].strip()


def test_reported_volume_changes_and_optional_values_are_numeric():
    for row in _read_archive():
        for field in OPTIONAL_NON_NEGATIVE_FIELDS:
            if row[field].strip():
                value = _decimal(row, field)
                assert value >= 0, f"{field} cannot be negative."
                if field == "executions_count":
                    assert value == value.to_integral_value(), (
                        "executions_count must be a whole number."
                    )

        if row["change_pct_reported"].strip():
            _decimal(row, "change_pct_reported")


def test_each_record_keeps_source_provenance_and_quality_labels():
    for row in _read_archive():
        assert row["source_name"].strip()
        assert row["source_url"].strip()
        parsed_url = urlparse(row["source_url"])
        assert parsed_url.scheme == "https"
        assert parsed_url.netloc

        for field in ("price_type", "delay_status", "quality_status", "notes"):
            assert row[field].strip(), f"{field} must explain data semantics."

        if row["quality_status"] == "source_revision_conflict":
            assert "reconcil" in row["notes"].lower()


def test_archive_documentation_preserves_known_data_limitations():
    documentation = README_PATH.read_text(encoding="utf-8")
    assert any(
        phrase in documentation
        for phrase in (
            "The source displays volume rounded in thousands",
            "Rounded provider volume is not an exact share-level tape",
        )
    )
    assert any(
        phrase in documentation
        for phrase in ("share-level volume", "share-level tape")
    )
    assert any(
        phrase in documentation.lower()
        for phrase in (
            "cross-source reconciliation remains pending",
            "cross-source reconciliation pending",
            "pending reconciliation",
        )
    )
    assert any(
        phrase in documentation.lower()
        for phrase in (
            "not accepted as a production feed",
            "not a production-grade feed",
        )
    )
