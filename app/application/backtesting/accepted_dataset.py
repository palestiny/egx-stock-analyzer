from dataclasses import dataclass

from app.infrastructure.historical_dataset.acceptance import (
    HistoricalDatasetAcceptanceValidator,
)
from app.infrastructure.historical_dataset.models import HistoricalDatasetManifest


@dataclass(frozen=True)
class AcceptedHistoricalDataset:
    manifest: HistoricalDatasetManifest

    @property
    def dataset_id(self) -> str:
        return self.manifest.dataset_id

    @property
    def dataset_version(self) -> str:
        return self.manifest.dataset_version

    @property
    def market_artifact_sha256(self) -> str:
        return self.manifest.market_observations.sha256

    @property
    def financial_artifact_sha256(self) -> str:
        return self.manifest.financial_snapshots.sha256


def accept_historical_dataset(
    validator: HistoricalDatasetAcceptanceValidator,
) -> AcceptedHistoricalDataset:
    return AcceptedHistoricalDataset(manifest=validator.validate())
