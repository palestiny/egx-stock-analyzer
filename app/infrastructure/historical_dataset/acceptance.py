from pathlib import Path

from app.infrastructure.historical_dataset.loader import (
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
            self._validate_raw_source_evidence(manifest)
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
            required_values = {
                "provider": provenance.provider,
                "source_url": provenance.source_url,
                "corporate_action_convention": provenance.corporate_action_convention,
                "licensing_notes": provenance.licensing_notes,
                "transformation_manifest": provenance.transformation_manifest,
            }
            if any(not value.strip() for value in required_values.values()):
                raise HistoricalDatasetAcceptanceError(
                    f"{artifact_name} provenance contains an empty acceptance field"
                )
            if not provenance.symbol_mappings:
                raise HistoricalDatasetAcceptanceError(
                    f"{artifact_name} provenance symbol mappings are required"
                )
            if provenance.acquired_at.tzinfo is None or provenance.acquired_at.utcoffset() is None:
                raise HistoricalDatasetAcceptanceError(
                    f"{artifact_name} provenance acquisition time must be timezone-aware"
                )

    def _validate_raw_source_evidence(self, manifest: HistoricalDatasetManifest) -> None:
        root = self._root
        for artifact_name, artifact in (
            ("market_observations", manifest.market_observations),
            ("financial_snapshots", manifest.financial_snapshots),
        ):
            evidence = artifact.provenance.raw_source_evidence  # type: ignore[union-attr]
            reference = Path(evidence.reference)
            try:
                resolved = (root / reference).resolve()
                resolved.relative_to(root.resolve())
            except (OSError, ValueError) as exc:
                raise HistoricalDatasetAcceptanceError(
                    f"{artifact_name} raw source evidence escapes dataset root"
                ) from exc
            if not resolved.is_file():
                raise HistoricalDatasetAcceptanceError(
                    f"{artifact_name} raw source evidence file does not exist"
                )
            import hashlib

            digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
            if digest != evidence.sha256:
                raise HistoricalDatasetAcceptanceError(
                    f"{artifact_name} raw source evidence checksum mismatch"
                )

    @property
    def _root(self) -> Path:
        return self._loader._root
