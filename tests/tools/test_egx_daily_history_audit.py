import csv
import io
from pathlib import Path

import pytest

from tools.egx_daily_history_audit import EXPECTED_COLUMNS, audit_csv_text, audit_file


def row(**overrides: str) -> dict[str, str]:
    values = {
        "session_date": "2026-11-10",
        "instrument_type": "equity",
        "symbol": "COMI",
        "price_unit": "EGP",
        "open_value": "100",
        "high_value": "110",
        "low_value": "95",
        "close_value": "105",
        "volume_thousands_reported": "12.5",
        "change_pct_reported": "-1.25",
        "traded_value_egp": "",
        "executions_count": "",
        "source_name": "Investing.com",
        "source_url": "https://example.com/history",
        "retrieved_at": "2026-11-10T19:16:35+02:00",
        "price_type": "daily historical OHLCV",
        "delay_status": "historical table; exact quote latency not stated",
        "quality_status": "source_reported",
        "notes": "Provider-reported values retained.",
    }
    values.update(overrides)
    return values


def csv_text(*rows: dict[str, str]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=EXPECTED_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def test_audit_reports_canonical_rows_and_missing_optional_metrics() -> None:
    report = audit_csv_text(csv_text(row()))

    assert report["status"] == "clean"
    assert report["row_count"] == 1
    assert report["symbol_count"] == 1
    assert report["session_count"] == 1
    assert report["last_session_date"] == "2026-11-10"
    assert report["latest_session_row_count"] == 1
    assert report["latest_session_symbols"] == ["COMI"]
    assert report["missing_value_counts"] == {
        "executions_count": 1,
        "traded_value_egp": 1,
    }
    assert report["source_authenticity"] == "NOT_INDEPENDENTLY_VERIFIED"


def test_audit_accepts_negative_daily_change_and_date_only_retrieval_time() -> None:
    report = audit_csv_text(csv_text(row(
        change_pct_reported="-3.5",
        retrieved_at="2026-11-10",
    )))

    assert report["invalid_row_count"] == 0
    assert report["ohlc_inconsistency_count"] == 0


def test_audit_flags_ohlc_geometry_and_preserves_existing_review_label() -> None:
    report = audit_csv_text(csv_text(row(
        open_value="99",
        low_value="100",
        quality_status="ohlc_inconsistency_review",
    )))

    assert report["status"] == "completed_with_findings"
    assert report["ohlc_inconsistency_count"] == 1
    assert report["unlabelled_ohlc_inconsistency_count"] == 0
    assert report["review_row_count"] == 1
    assert report["ohlc_inconsistencies"][0]["symbol"] == "COMI"


def test_audit_flags_unlabelled_ohlc_inconsistency() -> None:
    report = audit_csv_text(csv_text(row(
        open_value="99",
        low_value="100",
        quality_status="source_reported",
    )))

    assert report["unlabelled_ohlc_inconsistency_count"] == 1
    assert report["invalid_row_count"] == 0


def test_audit_detects_duplicate_symbol_session_keys() -> None:
    report = audit_csv_text(csv_text(row(), row(close_value="106")))

    assert report["duplicate_extra_rows"] == 1
    assert report["duplicate_keys"] == [
        {"session_date": "2026-11-10", "symbol": "COMI", "count": 2}
    ]


def test_audit_rejects_schema_mismatch() -> None:
    content = csv_text(row()).replace("session_date", "date", 1)

    with pytest.raises(ValueError, match="CSV schema mismatch"):
        audit_csv_text(content)


def test_audit_marks_bad_source_metadata_and_unknown_quality_status() -> None:
    report = audit_csv_text(csv_text(row(
        source_url="not-a-url",
        quality_status="unreviewed_unknown",
    )))

    issues = set(report["invalid_rows"][0]["issues"])
    assert "invalid_source_url" in issues
    assert "unknown_quality_status" in issues


def test_audit_counts_malformed_rows_without_silently_accepting_them() -> None:
    content = csv_text(row()) + "2026-11-11,equity,EGAL\n"
    report = audit_csv_text(content)

    assert report["row_count"] == 2
    assert report["parsed_row_count"] == 1
    assert report["malformed_row_count"] == 1
    assert report["status"] == "completed_with_findings"


def test_audit_rejects_invalid_retrieval_timestamp_timezone() -> None:
    report = audit_csv_text(csv_text(row(retrieved_at="2026-11-10T19:16:35")))

    assert report["invalid_row_count"] == 1
    assert "retrieved_at_timezone_missing" in report["invalid_rows"][0]["issues"]


def test_repository_archive_is_auditable_without_modification() -> None:
    archive = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "market_history"
        / "egx_daily_history.csv"
    )
    original_bytes = archive.read_bytes()

    report = audit_file(archive)

    assert archive.read_bytes() == original_bytes
    assert report["row_count"] == report["parsed_row_count"]
    assert report["symbol_count"] > 0
    assert report["session_count"] > 0
    assert report["duplicate_extra_rows"] == 0
    assert report["malformed_row_count"] == 0
    assert report["unlabelled_ohlc_inconsistency_count"] == 0
    assert len(report["artifact"]["sha256"]) == 64


def test_row_classifications_are_mutually_exclusive_and_conservative() -> None:
    content = csv_text(
        row(symbol="CLEAN"),
        row(symbol="REVIEW", quality_status="ohlc_inconsistency_review"),
        row(symbol="INVALID", open_value="not-a-number"),
        row(symbol="DUP"),
        row(symbol="DUP", close_value="106"),
    )
    report = audit_csv_text(content)

    assert report["row_classification_counts"] == {
        "clean_ohlc_candidates": 1,
        "review_required": 1,
        "rejected_or_invalid": 3,
    }
    assert report["duplicate_row_count"] == 2
    assert report["analysis_eligibility"] == (
        "STRUCTURAL_CANDIDATE_ONLY_NOT_SOURCE_AUTHENTICATED"
    )


def test_snapshot_comparison_reports_added_removed_and_changed_without_mutation(
    tmp_path: Path,
) -> None:
    from tools.egx_daily_history_audit import compare_csv_files

    baseline = tmp_path / "baseline.csv"
    current = tmp_path / "current.csv"
    baseline.write_text(csv_text(
        row(symbol="KEEP"),
        row(symbol="CHANGE", close_value="105"),
        row(symbol="REMOVE"),
    ), encoding="utf-8")
    current.write_text(csv_text(
        row(symbol="KEEP"),
        row(symbol="CHANGE", close_value="106"),
        row(symbol="ADD"),
    ), encoding="utf-8")
    before = current.read_bytes()

    comparison = compare_csv_files(current, baseline)

    assert current.read_bytes() == before
    assert comparison["status"] == "complete"
    assert comparison["added_count"] == 1
    assert comparison["added_keys"] == [
        {"session_date": "2026-11-10", "symbol": "ADD"}
    ]
    assert comparison["removed_count"] == 1
    assert comparison["removed_keys"] == [
        {"session_date": "2026-11-10", "symbol": "REMOVE"}
    ]
    assert comparison["changed_count"] == 1
    assert comparison["changed_rows"][0]["symbol"] == "CHANGE"
    assert comparison["changed_rows"][0]["changed_fields"] == ["close_value"]


def test_snapshot_comparison_marks_duplicate_keys_as_partial(tmp_path: Path) -> None:
    from tools.egx_daily_history_audit import compare_csv_files

    baseline = tmp_path / "baseline.csv"
    current = tmp_path / "current.csv"
    baseline.write_text(csv_text(row(symbol="DUP"), row(symbol="DUP")), encoding="utf-8")
    current.write_text(csv_text(row(symbol="DUP")), encoding="utf-8")

    comparison = compare_csv_files(current, baseline)

    assert comparison["status"] == "partial_due_to_duplicate_keys"
    assert comparison["comparison_complete"] is False
    assert comparison["ambiguous_duplicate_keys"] == [
        {"session_date": "2026-11-10", "symbol": "DUP"}
    ]
