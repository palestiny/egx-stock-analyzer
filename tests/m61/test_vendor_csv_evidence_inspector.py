from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tools.m61_vendor_csv_evidence_inspector import inspect_csv


def _write_csv(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_inspector_reports_hash_coverage_and_never_claims_acceptance(tmp_path: Path) -> None:
    content = (
        "Date,Open,High,Low,Close,Volume,Value (EGP)\n"
        "2020-01-02,10.0,11.0,9.0,10.5,1000,10500\n"
        "2021-01-04,10.5,12.0,10.0,11.5,1200,13800\n"
    )
    path = _write_csv(tmp_path / "COMI.csv", content)
    report = inspect_csv(path, "comi", "EGX.news", "order-reference")

    assert report["status"] == "CANDIDATE_ONLY"
    assert report["acceptance_claim"] is False
    assert report["symbol"] == "COMI"
    assert report["artifact"]["sha256"] == hashlib.sha256(content.encode()).hexdigest()
    assert report["artifact"]["row_count"] == 2
    assert report["coverage"]["first_date"] == "2020-01-02"
    assert report["source_license_verified"] is False
    assert report["point_in_time_financial_data_included"] is False


def test_inspector_finds_duplicate_and_out_of_order_dates(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path / "COMI.csv",
        "Date,Open,High,Low,Close,Volume\n"
        "2021-01-05,10,11,9,10,100\n"
        "2021-01-05,10,11,9,10,100\n"
        "2021-01-04,10,11,9,10,100\n",
    )
    report = inspect_csv(path, "COMI", "provider", "source")
    assert any("duplicate_date=2021-01-05" in item for item in report["validation_findings"])
    assert any("out_of_order=2021-01-04" in item for item in report["validation_findings"])


def test_inspector_finds_invalid_ohlc_and_negative_volume(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path / "COMI.csv",
        "Date,Open,High,Low,Close,Volume\n"
        "2021-01-04,12,11,13,10,-1\n",
    )
    report = inspect_csv(path, "COMI", "provider", "source")
    assert "row[0]:low_above_high" in report["validation_findings"]
    assert "row[0]:negative_volume" in report["validation_findings"]


def test_inspector_reports_malformed_rows_without_silently_dropping_them(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path / "COMI.csv",
        "Date,Open,High,Low,Close,Volume\n"
        "2021-01-04,10,11,9,10,100\n"
        "not-a-date,10,11,9,10,100\n",
    )
    report = inspect_csv(path, "COMI", "provider", "source")
    assert report["artifact"]["row_count"] == 2
    assert report["artifact"]["valid_row_count"] == 1
    assert len(report["row_errors"]) == 1


def test_inspector_rejects_missing_required_column(tmp_path: Path) -> None:
    path = _write_csv(tmp_path / "COMI.csv", "Date,Open,High,Low,Close\n2021-01-04,10,11,9,10\n")
    with pytest.raises(ValueError, match="Missing required CSV column for volume"):
        inspect_csv(path, "COMI", "provider", "source")


def test_inspector_accepts_utf8_bom_and_quoted_thousands_separators(tmp_path: Path) -> None:
    path = tmp_path / "COMI.csv"
    content = "\\n".join(
        [
            "Date,Open,High,Low,Close,Volume",
            '2021-01-04,"1,200","1,300","1,100","1,250","1,234"',
            "",
        ]
    )
    path.write_text(content, encoding="utf-8-sig")
    report = inspect_csv(path, "COMI", "provider", "source")
    assert report["artifact"]["valid_row_count"] == 1
    assert report["row_errors"] == []
