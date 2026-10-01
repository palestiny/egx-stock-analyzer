import json
from pathlib import Path

import pytest

from app.infrastructure.historical_dataset.acceptance import (
    HistoricalDatasetAcceptanceError,
    HistoricalDatasetAcceptanceValidator,
)
from app.infrastructure.historical_dataset.loader import HistoricalDatasetLoader

FIXTURE = Path("tests/fixtures/historical_dataset/v1")


def test_accepts_complete_reproducible_fixture() -> None:
    validator = HistoricalDatasetAcceptanceValidator(HistoricalDatasetLoader(FIXTURE), FIXTURE)

    manifest = validator.validate()

    assert manifest.dataset_id == "egx-m61-fixture"
    assert manifest.dataset_version == "3.0.0"


def test_rejects_raw_evidence_path_escape(tmp_path: Path) -> None:
    _copy_fixture(tmp_path)
    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    payload["market_observations_artifact"]["provenance"]["raw_source_evidence"]["reference"] = "../market_observations.csv"
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    validator = HistoricalDatasetAcceptanceValidator(HistoricalDatasetLoader(tmp_path), tmp_path)

    with pytest.raises(HistoricalDatasetAcceptanceError, match="must stay inside dataset root"):
        validator.validate()


def test_rejects_raw_evidence_checksum_mismatch(tmp_path: Path) -> None:
    _copy_fixture(tmp_path)
    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    payload["market_observations_artifact"]["provenance"]["raw_source_evidence"]["sha256"] = "0" * 64
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    validator = HistoricalDatasetAcceptanceValidator(HistoricalDatasetLoader(tmp_path), tmp_path)

    with pytest.raises(HistoricalDatasetAcceptanceError, match="checksum mismatch"):
        validator.validate()


def test_rejects_empty_corporate_action_convention(tmp_path: Path) -> None:
    _copy_fixture(tmp_path)
    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    payload["market_observations_artifact"]["provenance"]["corporate_action_convention"] = ""
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    validator = HistoricalDatasetAcceptanceValidator(HistoricalDatasetLoader(tmp_path), tmp_path)

    with pytest.raises(HistoricalDatasetAcceptanceError, match="empty acceptance field"):
        validator.validate()


def _copy_fixture(tmp_path: Path) -> None:
    for name in ("manifest.json", "market_observations.csv", "financial_snapshots.csv"):
        (tmp_path / name).write_bytes((FIXTURE / name).read_bytes())
