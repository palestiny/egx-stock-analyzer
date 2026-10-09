from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from tools.m61_comi_evidence_intake import _coverage_counts, _resolve_symbol_mapping, build_report


FIXTURE = Path("tests/fixtures/historical_dataset/v1")
STOCK_ID = UUID("00000000-0000-0000-0000-000000000001")


def test_comi_intake_rejects_synthetic_fixture_without_m61_coverage() -> None:
    report = build_report(FIXTURE)

    assert report["status"] == "REJECTED"
    assert report["checks"]["manifest"] == "PASS"
    assert report["checks"]["raw_source_evidence"] == "PASS"
    assert report["checks"]["comi_identity_mapping"] == "FAIL"
    assert report["checks"].get("252_warmup") is None
    assert report["checks"].get("financial_artifact") is None


def test_comi_intake_never_accepts_missing_dataset() -> None:
    report = build_report(FIXTURE / "does-not-exist")

    assert report["status"] == "REJECTED"
    assert report["errors"]


def test_symbol_mapping_requires_exactly_one_valid_comi_mapping() -> None:
    assert _resolve_symbol_mapping(
        (f"COMI -> {STOCK_ID}", "EGAL -> {STOCK_ID}"),
        "COMI",
    ) == STOCK_ID


def test_symbol_mapping_rejects_ambiguous_comi_mapping() -> None:
    other = UUID("00000000-0000-0000-0000-000000000002")

    assert _resolve_symbol_mapping(
        (f"COMI -> {STOCK_ID}", f"COMI -> {other}"),
        "COMI",
    ) is None


def test_symbol_mapping_rejects_malformed_comi_mapping() -> None:
    assert _resolve_symbol_mapping(("COMI -> not-a-uuid",), "COMI") is None



def test_comi_coverage_counts_unique_sessions_across_full_warmup_history() -> None:
    start = datetime(2019, 1, 1, tzinfo=timezone.utc)
    timestamps = [start + timedelta(days=offset) for offset in range(252)]
    timestamps.extend([timestamps[0], datetime(2021, 1, 4, tzinfo=timezone.utc)])

    dates, warmup, evaluation = _coverage_counts(timestamps)

    assert len(dates) == 253
    assert warmup == 252
    assert evaluation == 1


def test_comi_coverage_uses_cairo_local_session_date() -> None:
    # 22:30 UTC on 2020-12-31 is already 2021-01-01 in Cairo.
    timestamp = datetime(2020, 12, 31, 22, 30, tzinfo=timezone.utc)

    dates, warmup, evaluation = _coverage_counts([timestamp])

    assert dates == [date(2021, 1, 1)]
    assert warmup == 0
    assert evaluation == 1
