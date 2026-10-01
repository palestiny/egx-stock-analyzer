from dataclasses import dataclass
from decimal import Decimal

from app.domain.backtesting.simulator import BacktestConfiguration, BacktestResult


class BacktestValidationEvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class BacktestValidationEvidence:
    dataset_id: str
    dataset_version: str
    dataset_market_artifact_sha256: str
    dataset_financial_artifact_sha256: str
    strategy_id: str
    strategy_version: str
    repository_commit: str
    runtime: str
    configuration: BacktestConfiguration
    result: BacktestResult

    def __post_init__(self) -> None:
        required = {
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "dataset_market_artifact_sha256": self.dataset_market_artifact_sha256,
            "dataset_financial_artifact_sha256": self.dataset_financial_artifact_sha256,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "repository_commit": self.repository_commit,
            "runtime": self.runtime,
        }
        if any(not value.strip() for value in required.values()):
            raise BacktestValidationEvidenceError(
                "Backtest validation evidence contains an empty reproducibility field"
            )
        if self.result.strategy_id != self.strategy_id:
            raise BacktestValidationEvidenceError(
                "Backtest result strategy_id does not match validation evidence"
            )
        if self.result.strategy_version != self.strategy_version:
            raise BacktestValidationEvidenceError(
                "Backtest result strategy_version does not match validation evidence"
            )
        if self.result.configuration != self.configuration:
            raise BacktestValidationEvidenceError(
                "Backtest result configuration does not match validation evidence"
            )
        for digest in (
            self.dataset_market_artifact_sha256,
            self.dataset_financial_artifact_sha256,
        ):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.lower()):
                raise BacktestValidationEvidenceError(
                    "Dataset artifact checksums must be SHA-256 digests"
                )
        if not self.configuration.transaction_cost_rate >= Decimal("0"):
            raise BacktestValidationEvidenceError("Transaction cost rate cannot be negative")
        if not self.configuration.slippage_rate >= Decimal("0"):
            raise BacktestValidationEvidenceError("Slippage rate cannot be negative")
