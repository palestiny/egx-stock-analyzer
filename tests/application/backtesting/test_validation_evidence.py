from decimal import Decimal
from pathlib import Path

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


def accepted_dataset() -> AcceptedHistoricalDataset:
    artifact = DatasetArtifact(
        path=Path("market.csv"),
        sha256="a" * 64,
        row_count=1,
        coverage=DatasetCoverage("2026-01-01", "2026-01-01", 1),
    )
    financial = DatasetArtifact(
        path=Path("financial.csv"),
        sha256="b" * 64,
        row_count=1,
        coverage=DatasetCoverage("2026-01-01", "2026-01-01", 1),
    )
    return AcceptedHistoricalDataset(
        HistoricalDatasetManifest(
            dataset_id="egx-m61",
            dataset_version="1.0.0",
            schema_version="1.0",
            market_observations=artifact,
            financial_snapshots=financial,
        )
    )


def result() -> BacktestResult:
    configuration = BacktestConfiguration(
        max_holding_bars=5,
        transaction_cost_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
    )
    return BacktestResult("strategy-v0", "1", configuration, (), 0)


def evidence() -> BacktestValidationEvidence:
    return BacktestValidationEvidence(
        accepted_dataset=accepted_dataset(),
        strategy_id="strategy-v0",
        strategy_version="1",
        repository_commit="abc123",
        runtime="python-3.13",
        configuration=result().configuration,
        result=result(),
    )


def test_accepts_reproducibility_metadata() -> None:
    item = evidence()

    assert item.accepted_dataset.dataset_id == "egx-m61"
    assert item.result == result()


def test_rejects_strategy_identity_mismatch() -> None:
    with pytest.raises(BacktestValidationEvidenceError, match="strategy_id"):
        BacktestValidationEvidence(
            accepted_dataset=accepted_dataset(),
            strategy_id="other",
            strategy_version="1",
            repository_commit="abc123",
            runtime="python-3.13",
            configuration=result().configuration,
            result=result(),
        )


def test_rejects_result_configuration_mismatch() -> None:
    configuration = BacktestConfiguration(
        max_holding_bars=6,
        transaction_cost_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
    )
    with pytest.raises(BacktestValidationEvidenceError, match="configuration"):
        BacktestValidationEvidence(
            accepted_dataset=accepted_dataset(),
            strategy_id="strategy-v0",
            strategy_version="1",
            repository_commit="abc123",
            runtime="python-3.13",
            configuration=configuration,
            result=result(),
        )
