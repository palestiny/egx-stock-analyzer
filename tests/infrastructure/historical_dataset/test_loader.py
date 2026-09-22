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

    assert rows[0].open == "10.00"
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
    payload["market_observations_artifact"]["row_count"] = 4
    import hashlib
    payload["market_observations_artifact"]["sha256"] = hashlib.sha256(
        (tmp_path / "market_observations.csv").read_bytes()
    ).hexdigest()
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HistoricalDatasetIntegrityError, match="Duplicate market observation"):
        HistoricalDatasetLoader(tmp_path).load_market_observations()
