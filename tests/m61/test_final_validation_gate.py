from pathlib import Path

from tools.m61_final_validation_gate import build_report


def test_final_gate_blocks_when_real_evidence_package_is_missing(tmp_path: Path) -> None:
    report = build_report(tmp_path)

    assert report["status"] == "BLOCKED"
    assert report["errors"]


def test_final_gate_does_not_accept_repository_fixture_as_final_evidence() -> None:
    fixture = Path("tests/fixtures/historical_dataset/v1")
    report = build_report(fixture)

    assert report["status"] == "BLOCKED"
