import hashlib
import json
from pathlib import Path

import pytest

from app.infrastructure.historical_dataset.loader import (
    HistoricalDatasetIntegrityError,
    HistoricalDatasetLoader,
)

FIXTURE = Path("tests/fixtures/historical_dataset/v1")


def test_loads_manifest_and_verifies_artifacts() -> None:
    manifest = HistoricalDatasetLoader(FIXTURE).load_manifest()

    assert manifest.dataset_id == "egx-m61-fixture"
    assert manifest.dataset_version == "1.0.0"
    assert manifest.schema_version == "1"


def test_loads_decimal_market_values_without_float_conversion() -> None:
    rows = HistoricalDatasetLoader(FIXTURE).load_market_observations()

    assert str(rows[0].open) == "10.00"
    assert rows[0].open.as_tuple().exponent == -2


def test_rejects_checksum_mismatch(tmp_path: Path) -> None:
    source = FIXTURE / "manifest.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["market_observations_artifact"]["sha256"] = "0" * 64
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "market_observations.csv").write_bytes(
        (FIXTURE / "market_observations.csv").read_bytes()
    )
    (tmp_path / "financial_snapshots.csv").write_bytes(
        (FIXTURE / "financial_snapshots.csv").read_bytes()
    )

    with pytest.raises(HistoricalDatasetIntegrityError, match="checksum mismatch"):
        HistoricalDatasetLoader(tmp_path).load_manifest()


def test_rejects_duplicate_market_observation(tmp_path: Path) -> None:
    for name in ("manifest.json", "financial_snapshots.csv"):
        (tmp_path / name).write_bytes((FIXTURE / name).read_bytes())
    original = (FIXTURE / "market_observations.csv").read_text(encoding="utf-8")
    lines = original.splitlines()
    (tmp_path / "market_observations.csv").write_text(
        original + lines[-1] + "\n", encoding="utf-8"
    )
    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    payload["market_observations_artifact"]["row_count"] = len(lines)
    payload["market_observations_artifact"]["sha256"] = hashlib.sha256(
        (tmp_path / "market_observations.csv").read_bytes()
    ).hexdigest()
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HistoricalDatasetIntegrityError, match="Duplicate market observation"):
        HistoricalDatasetLoader(tmp_path).load_market_observations()


def _copy_fixture(tmp_path: Path) -> None:
    for name in ("manifest.json", "market_observations.csv", "financial_snapshots.csv"):
        (tmp_path / name).write_bytes((FIXTURE / name).read_bytes())


def test_rejects_manifest_with_unknown_field(tmp_path: Path) -> None:
    _copy_fixture(tmp_path)
    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    payload["unexpected"] = True
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HistoricalDatasetIntegrityError, match="manifest schema is invalid"):
        HistoricalDatasetLoader(tmp_path).load_manifest()


def test_rejects_market_row_count_mismatch(tmp_path: Path) -> None:
    _copy_fixture(tmp_path)
    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    payload["market_observations_artifact"]["row_count"] = 999
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HistoricalDatasetIntegrityError, match="row count mismatch"):
        HistoricalDatasetLoader(tmp_path).load_market_observations()


def test_rejects_malformed_financial_row(tmp_path: Path) -> None:
    _copy_fixture(tmp_path)
    source = (tmp_path / "financial_snapshots.csv").read_text(encoding="utf-8")
    lines = source.splitlines()
    lines[1] = lines[1].replace("900000.00", "not-a-decimal")
    (tmp_path / "financial_snapshots.csv").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    payload["financial_snapshots_artifact"]["sha256"] = hashlib.sha256(
        (tmp_path / "financial_snapshots.csv").read_bytes()
    ).hexdigest()
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HistoricalDatasetIntegrityError, match="Invalid financial snapshot"):
        HistoricalDatasetLoader(tmp_path).load_financial_snapshots()


def test_rejects_financial_snapshot_available_before_period_end(tmp_path: Path) -> None:
    _copy_fixture(tmp_path)
    source = (tmp_path / "financial_snapshots.csv").read_text(encoding="utf-8")
    lines = source.splitlines()
    lines[1] = lines[1].replace("2025-02-15", "2024-12-30")
    (tmp_path / "financial_snapshots.csv").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    payload["financial_snapshots_artifact"]["sha256"] = hashlib.sha256(
        (tmp_path / "financial_snapshots.csv").read_bytes()
    ).hexdigest()
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        HistoricalDatasetIntegrityError,
        match="available_at cannot precede period_end",
    ):
        HistoricalDatasetLoader(tmp_path).load_financial_snapshots()


def test_financial_snapshots_are_deterministic() -> None:
    loader = HistoricalDatasetLoader(FIXTURE)

    first = loader.load_financial_snapshots()
    second = loader.load_financial_snapshots()

    assert first == second


def test_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    _copy_fixture(tmp_path)
    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    payload["schema_version"] = "2"
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        HistoricalDatasetIntegrityError,
        match="Unsupported historical dataset schema version",
    ):
        HistoricalDatasetLoader(tmp_path).load_manifest()


def test_rejects_unpinned_or_unapproved_artifact_path(tmp_path: Path) -> None:
    _copy_fixture(tmp_path)
    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    payload["market_observations_artifact"]["path"] = "unexpected.csv"
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        HistoricalDatasetIntegrityError,
        match="Artifact path is not allowed",
    ):
        HistoricalDatasetLoader(tmp_path).load_manifest()


def test_rejects_invalid_sha256_format(tmp_path: Path) -> None:
    _copy_fixture(tmp_path)
    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    payload["market_observations_artifact"]["sha256"] = "not-a-sha"
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        HistoricalDatasetIntegrityError,
        match="sha256 must be a 64-character hexadecimal digest",
    ):
        HistoricalDatasetLoader(tmp_path).load_manifest()
