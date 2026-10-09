from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from tools.m61_comi_evidence_intake import (
    _corporate_action_convention_is_explicit,
    _coverage_counts,
    _financial_availability_years,
    _license_attestation_is_explicit,
    _resolve_symbol_mapping,
    build_report,
)


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



def test_license_gate_requires_explicit_verified_scope_and_reference() -> None:
    assert _license_attestation_is_explicit(
        "status=verified; evidence_reference=contract-2026-001; "
        "permitted_uses=local_storage,historical_research,backtesting; "
        "redistribution=prohibited"
    )
    assert not _license_attestation_is_explicit("test fixture only; not external market data")
    assert not _license_attestation_is_explicit(
        "status=verified; evidence_reference=contract-2026-001; "
        "permitted_uses=local_storage,historical_research; redistribution=prohibited"
    )


def test_corporate_action_gate_rejects_unknown_conventions() -> None:
    assert _corporate_action_convention_is_explicit("raw-as-published")
    assert _corporate_action_convention_is_explicit("split-adjusted")
    assert not _corporate_action_convention_is_explicit("unknown")
    assert not _corporate_action_convention_is_explicit("")


def test_financial_availability_coverage_uses_evaluation_years_only() -> None:
    snapshots = [
        SimpleNamespace(available_at=date(year, 6, 1))
        for year in range(2021, 2027)
    ]

    assert _financial_availability_years(snapshots) == [2021, 2022, 2023, 2024, 2025]


def test_financial_availability_coverage_preserves_missing_years() -> None:
    snapshots = [
        SimpleNamespace(available_at=date(2021, 6, 1)),
        SimpleNamespace(available_at=date(2023, 6, 1)),
        SimpleNamespace(available_at=date(2026, 2, 1)),
    ]

    assert _financial_availability_years(snapshots) == [2021, 2023]
