from decimal import Decimal
from datetime import datetime, timezone

import pytest

from app.application.backtesting.validation_evidence import (
    BacktestValidationEvidence,
    BacktestValidationEvidenceError,
)
from app.domain.backtesting.simulator import (
    BacktestConfiguration,
    BacktestResult,
)


def result() -> BacktestResult:
    configuration = BacktestConfiguration(
        max_holding_bars=5,
        transaction_cost_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
    )
    return BacktestResult(
        strategy_id="strategy-v0",
        strategy_version="1",
        configuration=configuration,
        trades=(),
        open_trade_count=0,
    )


def evidence() -> BacktestValidationEvidence:
    return BacktestValidationEvidence(
        dataset_id="egx-m61",
        dataset_version="1.0.0",
        dataset_market_artifact_sha256="a" * 64,
        dataset_financial_artifact_sha256="b" * 64,
        strategy_id="strategy-v0",
        strategy_version="1",
        repository_commit="abc123",
        runtime="python-3.13",
        configuration=result().configuration,
        result=result(),
    )


def test_accepts_reproducibility_metadata() -> None:
    item = evidence()

    assert item.dataset_id == "egx-m61"
    assert item.result == result()


def test_rejects_strategy_identity_mismatch() -> None:
    with pytest.raises(BacktestValidationEvidenceError, match="strategy_id"):
        BacktestValidationEvidence(
            **{**evidence().__dict__, "strategy_id": "other"}
        )


def test_rejects_invalid_dataset_checksum() -> None:
    with pytest.raises(BacktestValidationEvidenceError, match="SHA-256"):
        BacktestValidationEvidence(
            **{**evidence().__dict__, "dataset_market_artifact_sha256": "invalid"}
        )
