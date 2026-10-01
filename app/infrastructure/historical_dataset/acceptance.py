from app.infrastructure.historical_dataset.loader import (
    HistoricalDatasetAcceptanceError,
    HistoricalDatasetIntegrityError,
    HistoricalDatasetLoader,
)
from app.infrastructure.historical_dataset.models import HistoricalDatasetManifest


class HistoricalDatasetAcceptanceError(ValueError):
    pass


class HistoricalDatasetAcceptanceValidator:
    """Gate a historical dataset before it can be used for strategy evaluation."""

    def __init__(self, loader: HistoricalDatasetLoader) -> None:
        self._loader = loader

    def validate(self) -> HistoricalDatasetManifest:
        try:
            manifest = self._loader.load_manifest()
            self._loader.load_market_observations()
            self._loader.load_financial_snapshots()
            self._validate_provenance(manifest)
            self._loader.verify_raw_source_evidence(manifest)
            return manifest
        except HistoricalDatasetIntegrityError as exc:
            raise HistoricalDatasetAcceptanceError(str(exc)) from exc

    def _validate_provenance(self, manifest: HistoricalDatasetManifest) -> None:
        for artifact_name, artifact in (
            ("market_observations", manifest.market_observations),
            ("financial_snapshots", manifest.financial_snapshots),
        ):
            provenance = artifact.provenance
            if provenance is None:
                raise HistoricalDatasetAcceptanceError(
                    f"{artifact_name} artifact provenance is required for backtest acceptance"
                )
            required_values = (
                provenance.provider,
                provenance.source_url,
                provenance.corporate_action_convention,
                provenance.licensing_notes,
                provenance.transformation_manifest,
            )
            if any(not value.strip() for value in required_values):
                raise HistoricalDatasetAcceptanceError(
                    f"{artifact_name} provenance contains an empty acceptance field"
                )
            if not provenance.symbol_mappings:
                raise HistoricalDatasetAcceptanceError(
                    f"{artifact_name} provenance symbol mappings are required"
                )
            if not provenance.raw_source_evidence.reference.strip():
                raise HistoricalDatasetAcceptanceError(
                    f"{artifact_name} raw source evidence reference is required"
                )
