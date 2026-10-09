from datetime import date
from pathlib import Path

import pytest

from app.infrastructure.historical_dataset.loader import HistoricalDatasetLoader
from tools.m61_generate_test_dataset import build_test_dataset


def test_generator_creates_loadable_full_cohort_test_dataset(tmp_path: Path) -> None:
    output = tmp_path / "dataset"
    summary = build_test_dataset(output, date(2019, 1, 1), date(2025, 12, 31))

    loader = HistoricalDatasetLoader(output)
    manifest = loader.load_manifest()
    market = loader.load_market_observations()
    financial = loader.load_financial_snapshots()

    assert summary["dataset_id"] == "m61-synthetic-test-only"
    assert summary["symbols"] == 10
    assert summary["market_rows"] > 10_000
    assert summary["financial_rows"] == 80
    assert manifest.dataset_id == "m61-synthetic-test-only"
    assert len({item.stock_id for item in market}) == 10
    assert market[0].timestamp.date() == date(2019, 1, 1)
    assert market[-1].timestamp.date() == date(2025, 12, 31)
    assert len(financial) == 80
    assert all(item.source == "synthetic-test-generator" for item in market)
    assert all(item.source == "synthetic-test-generator" for item in financial)
    loader.verify_raw_source_evidence()


def test_generator_is_deterministic_except_acquisition_timestamp(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    build_test_dataset(first, date(2021, 1, 1), date(2021, 1, 8))
    build_test_dataset(second, date(2021, 1, 1), date(2021, 1, 8))

    assert (first / "market_observations.csv").read_bytes() == (
        second / "market_observations.csv"
    ).read_bytes()
    assert (first / "financial_snapshots.csv").read_bytes() == (
        second / "financial_snapshots.csv"
    ).read_bytes()
    first_manifest = HistoricalDatasetLoader(first).load_manifest()
    second_manifest = HistoricalDatasetLoader(second).load_manifest()
    assert first_manifest.dataset_id == second_manifest.dataset_id
    assert first_manifest.market_observations.sha256 == second_manifest.market_observations.sha256


def test_generator_refuses_to_overwrite_existing_data(tmp_path: Path) -> None:
    output = tmp_path / "dataset"
    output.mkdir()
    (output / "keep.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="empty or absent"):
        build_test_dataset(output, date(2021, 1, 1), date(2021, 1, 8))
