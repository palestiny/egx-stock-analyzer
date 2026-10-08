from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.application.research.dataset_repository import ResearchDataset
from app.domain.research.dataset import PriceAdjustment, ResearchBar, ResearchDataQuality
from app.infrastructure.persistence.sqlite_research_dataset_repository import (
    ResearchDatasetConflictError,
    SQLiteResearchDatasetRepository,
)


def bar(day: int, *, close="100", quality=ResearchDataQuality.VALID):
    timestamp = datetime(2026, 10, day, tzinfo=timezone.utc)
    return ResearchBar(
        "COMI", "1d", timestamp, timestamp, Decimal("100"), Decimal("105"),
        Decimal("95"), Decimal(close), Decimal("1000"), "fixture", "v1",
        quality, PriceAdjustment.UNADJUSTED,
    )


def dataset(bars=None):
    return ResearchDataset(
        "COMI", "1d", "fixture", "v1", PriceAdjustment.UNADJUSTED,
        tuple(bars if bars is not None else (bar(1), bar(2, close="101"))),
    )


def load(repo):
    return repo.get(
        symbol="COMI", timeframe="1d", provider="fixture",
        version="v1", adjustment=PriceAdjustment.UNADJUSTED,
    )


def test_register_round_trip_and_reopen_preserves_exact_bars(tmp_path):
    path = tmp_path / "research.sqlite"
    first = SQLiteResearchDatasetRepository(path)
    fingerprint = first.register(dataset())
    reopened = SQLiteResearchDatasetRepository(path)
    loaded = load(reopened)
    assert loaded == dataset()
    assert reopened.register(loaded) == fingerprint


def test_same_identity_with_different_contents_requires_new_version(tmp_path):
    repo = SQLiteResearchDatasetRepository(tmp_path / "research.sqlite")
    repo.register(dataset())
    with pytest.raises(ResearchDatasetConflictError, match="publish a new version"):
        repo.register(dataset((bar(1), bar(2, close="102"))))


def test_exact_lookup_does_not_substitute_versions(tmp_path):
    repo = SQLiteResearchDatasetRepository(tmp_path / "research.sqlite")
    repo.register(dataset())
    assert repo.get(
        symbol="COMI", timeframe="1d", provider="fixture",
        version="v2", adjustment=PriceAdjustment.UNADJUSTED,
    ) is None


def test_mixed_identity_is_rejected_before_storage(tmp_path):
    repo = SQLiteResearchDatasetRepository(tmp_path / "research.sqlite")
    with pytest.raises(ValueError, match="match the registered dataset identity"):
        repo.register(dataset((bar(1), ResearchBar(
            "EGAL", "1d", datetime(2026, 10, 2, tzinfo=timezone.utc),
            datetime(2026, 10, 2, tzinfo=timezone.utc), Decimal("100"),
            Decimal("105"), Decimal("95"), Decimal("100"), Decimal("1000"),
            "fixture", "v1", ResearchDataQuality.VALID, PriceAdjustment.UNADJUSTED,
        )))
    assert load(repo) is None


def test_duplicate_timestamp_is_rejected(tmp_path):
    repo = SQLiteResearchDatasetRepository(tmp_path / "research.sqlite")
    with pytest.raises(ValueError, match="duplicate source timestamp"):
        repo.register(dataset((bar(1), bar(1, close="101"))))


def test_invalid_quality_is_preserved_for_engine_to_fail_closed(tmp_path):
    repo = SQLiteResearchDatasetRepository(tmp_path / "research.sqlite")
    invalid = dataset((bar(1, quality=ResearchDataQuality.PARTIAL),))
    repo.register(invalid)
    assert load(repo) == invalid
