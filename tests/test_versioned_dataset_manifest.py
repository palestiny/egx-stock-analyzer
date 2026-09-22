import hashlib
import json
from datetime import date

import pytest

from app.application.backtesting.versioned_dataset import (
    DatasetIntegrityError,
    DatasetManifestError,
    VersionedDatasetManifest,
)


def manifest(**overrides):
    value = {
        "dataset_id": "egx-strategy-v0",
        "version": "2026-09-22.1",
        "schema_version": "1",
        "artifact_uri": "https://example.invalid/egx/2026-09-22.1",
        "sha256": "a" * 64,
        "coverage_start": "2020-01-01",
        "coverage_end": "2026-09-19",
        "provenance": {
            "source": "test-export",
            "exported_at": "2026-09-22T20:00:00+00:00",
        },
    }
    value.update(overrides)
    return value


def test_manifest_parses_immutable_identity_and_coverage():
    result = VersionedDatasetManifest.from_dict(manifest())

    assert result.dataset_id == "egx-strategy-v0"
    assert result.version == "2026-09-22.1"
    assert result.schema_version == "1"
    assert result.sha256 == "a" * 64
    assert result.coverage_start == date(2020, 1, 1)
    assert result.coverage_end == date(2026, 9, 19)


@pytest.mark.parametrize(
    "field,value",
    [
        ("dataset_id", ""),
        ("version", ""),
        ("schema_version", ""),
        ("artifact_uri", ""),
        ("sha256", "not-a-sha"),
        ("coverage_start", "2026-09-20"),
        ("coverage_end", "2020-01-01"),
    ],
)
def test_manifest_rejects_invalid_contract(field, value):
    with pytest.raises(DatasetManifestError):
        VersionedDatasetManifest.from_dict(manifest(**{field: value}))


def test_manifest_rejects_missing_required_field():
    payload = manifest()
    del payload["sha256"]

    with pytest.raises(DatasetManifestError):
        VersionedDatasetManifest.from_dict(payload)


def test_manifest_round_trip_is_deterministic():
    result = VersionedDatasetManifest.from_dict(manifest())

    assert result.to_dict() == manifest()


def test_manifest_json_round_trip_preserves_contract():
    result = VersionedDatasetManifest.from_json(
        json.dumps(manifest(), sort_keys=True)
    )

    assert result.to_dict() == manifest()


def test_integrity_validation_accepts_exact_artifact_bytes():
    artifact = b"deterministic historical fixture"
    expected = hashlib.sha256(artifact).hexdigest()
    result = VersionedDatasetManifest.from_dict(manifest(sha256=expected))

    result.verify_integrity(artifact)


def test_integrity_validation_rejects_mismatch():
    result = VersionedDatasetManifest.from_dict(manifest())

    with pytest.raises(DatasetIntegrityError):
        result.verify_integrity(b"tampered")


def test_date_range_is_inclusive():
    result = VersionedDatasetManifest.from_dict(manifest())

    assert result.covers(date(2020, 1, 1), date(2026, 9, 19))
    assert result.covers(date(2026, 9, 19), date(2026, 9, 19))
    assert not result.covers(date(2019, 12, 31), date(2026, 9, 19))
    assert not result.covers(date(2020, 1, 1), date(2026, 9, 20))
