from pathlib import Path

from tools.m61_comi_evidence_intake import build_report


FIXTURE = Path("tests/fixtures/historical_dataset/v1")


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
