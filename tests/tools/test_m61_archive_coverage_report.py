import pytest

from tools.m61_archive_coverage_report import build_report


def sample_audit() -> dict[str, object]:
    return {
        "audited_at_utc": "2026-10-20T14:36:05+00:00",
        "dataset_path": "data/normalized/yahoo/daily_prices.csv",
        "source_audit_path": "reports/data-quality-audit-2026-10-20.json",
        "per_symbol": {
            "COMI": {
                "rows": 100,
                "valid_ohlc_rows": 80,
                "invalid_ohlc_rows": 20,
                "first_session_date": "2021-10-20",
                "last_session_date": "2026-10-19",
            },
            "EGAL": {
                "rows": 50,
                "valid_ohlc_rows": 45,
                "invalid_ohlc_rows": 5,
                "first_session_date": "2022-01-01",
                "last_session_date": "2026-10-18",
            },
        },
    }


def test_build_report_sorts_symbols_and_summarizes_counts_and_global_dates() -> None:
    audit = sample_audit()
    report = build_report(audit)

    assert report["schema_version"] == 2
    assert report["status"] == "completed"
    assert report["source_audit_path"] == audit["source_audit_path"]
    assert report["source_audit_date"] == audit["audited_at_utc"]
    assert report["symbol_count"] == 2
    assert report["total_rows"] == 150
    assert report["valid_ohlc_rows"] == 125
    assert report["invalid_ohlc_rows"] == 25
    assert report["valid_ohlc_rows"] + report["invalid_ohlc_rows"] == report["total_rows"]
    assert report["valid_ohlc_pct"] == 83.33
    assert report["first_session_date"] == "2021-10-20"
    assert report["last_session_date"] == "2026-10-19"
    symbols = report["symbols_sorted_by_valid_rows_desc"]
    assert [item["symbol"] for item in symbols] == ["COMI", "EGAL"]
    assert symbols[0]["valid_ohlc_pct"] == 80.0
    assert sum(item["rows"] for item in symbols) == report["total_rows"]
    assert sum(item["valid_ohlc_rows"] for item in symbols) == report["valid_ohlc_rows"]
    assert sum(item["invalid_ohlc_rows"] for item in symbols) == report["invalid_ohlc_rows"]
    assert report["limitations"]


def test_build_report_rejects_inconsistent_per_symbol_counts() -> None:
    audit = sample_audit()
    audit["per_symbol"]["COMI"]["rows"] = 101  # type: ignore[index]

    with pytest.raises(ValueError, match="inconsistent row counts for COMI"):
        build_report(audit)


def test_build_report_rejects_empty_per_symbol_data() -> None:
    with pytest.raises(ValueError, match="non-empty per_symbol"):
        build_report({"per_symbol": {}})


def test_build_report_rejects_reversed_symbol_date_range() -> None:
    audit = sample_audit()
    audit["per_symbol"]["COMI"]["first_session_date"] = "2026-10-20"  # type: ignore[index]
    audit["per_symbol"]["COMI"]["last_session_date"] = "2021-10-20"  # type: ignore[index]

    with pytest.raises(ValueError, match="invalid date range for COMI"):
        build_report(audit)
