from decimal import Decimal

import pytest

from app.application.backtesting.accepted_dataset import AcceptedHistoricalDataset
from app.application.backtesting.validation_evidence import (
    BacktestValidationEvidence,
    BacktestValidationEvidenceError,
)
from app.domain.backtesting.simulator import BacktestConfiguration, BacktestResult
from app.infrastructure.historical_dataset.models import (
    DatasetArtifact,
    DatasetCoverage,
    HistoricalDatasetManifest,
)


def manifest() -> HistoricalDatasetManifest:
    artifact = DatasetArtifact(
        path=__import__("pathlib").Path("market.csv"),
        sha256="a" * 64,
        row_count=1,
        coverage=DatasetCoverage("2026-01-01", "2026-01-01", 1),
    )
    financial = DatasetArtifact(
        path=__import__("pathlib").Path("financial.csv"),
        sha256="b" * 64,
        row_count=1,
        coverage=DatasetCoverage("2026-01-01", "2026-01-01", 1),
    )
    return HistoricalDatasetManifest(
        dataset_id="egx-m61",
        dataset_version="1.0.0",
        schema_version="1.0",
        market_observations=artifact,
        financial_snapshots=financial,
    )


def result() -> BacktestResult:
    config = BacktestConfiguration(5, Decimal("0.001"), Decimal("0.0005"))
    return BacktestResult("strategy-v0", "1", config, (), 0)


def test_accepted_dataset_exposes_immutable_identity() -> None:
    accepted = AcceptedHistoricalDataset(manifest())

    assert accepted.dataset_id == "egx-m61"
    assert accepted.dataset_version == "1.0.0"
    assert accepted.market_artifact_sha256 == "a" * 64
    assert accepted.financial_artifact_sha256 == "b" * 64


def test_backtest_evidence_can_only_be_bound_to_matching_accepted_dataset() -> None:
    accepted = AcceptedHistoricalDataset(manifest())
    item = BacktestValidationEvidence(
        accepted_dataset=accepted,
        strategy_id="strategy-v0",
        strategy_version="1",
        repository_commit="abc123",
        runtime="python-3.13",
        configuration=result().configuration,
        result=result(),
    )

    assert item.accepted_dataset.dataset_id == "egx-m61"


def test_rejects_result_strategy_mismatch() -> None:
    accepted = AcceptedHistoricalDataset(manifest())
    mismatched = BacktestResult("other", "1", result().configuration, (), 0)

    with pytest.raises(BacktestValidationEvidenceError, match="strategy_id"):
        BacktestValidationEvidence(
            accepted_dataset=accepted,
            strategy_id="strategy-v0",
            strategy_version="1",
            repository_commit="abc123",
            runtime="python-3.13",
            configuration=result().configuration,
            result=mismatched,
        )
