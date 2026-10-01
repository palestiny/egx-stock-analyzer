import hashlib
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

    def __init__(self, loader: HistoricalDatasetLoader, root: Path) -> None:
        self._loader = loader
        self._root = root

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

    def _validate_raw_source_evidence(self, manifest: HistoricalDatasetManifest) -> None:
        root = self._root.resolve()
        for artifact_name, artifact in (
            ("market_observations", manifest.market_observations),
            ("financial_snapshots", manifest.financial_snapshots),
        ):
            evidence = artifact.provenance.raw_source_evidence  # type: ignore[union-attr]
            reference = Path(evidence.reference)
            if reference.is_absolute() or any(part == ".." for part in reference.parts):
                raise HistoricalDatasetAcceptanceError(
                    f"{artifact_name} raw source evidence must stay inside dataset root"
                )
            resolved = (root / reference).resolve()
            try:
                resolved.relative_to(root)
            except ValueError as exc:
                raise HistoricalDatasetAcceptanceError(
                    f"{artifact_name} raw source evidence escapes dataset root"
                ) from exc
            if not resolved.is_file():
                raise HistoricalDatasetAcceptanceError(
                    f"{artifact_name} raw source evidence file does not exist"
                )
            digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
            if digest != evidence.sha256:
                raise HistoricalDatasetAcceptanceError(
                    f"{artifact_name} raw source evidence checksum mismatch"
                )
