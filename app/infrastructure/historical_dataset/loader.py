import csv
import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from app.infrastructure.historical_dataset.models import (
    DatasetArtifact,
    DatasetCoverage,
    HistoricalDatasetManifest,
    HistoricalFinancialSnapshotRecord,
    HistoricalMarketObservation,
)


class HistoricalDatasetIntegrityError(ValueError):
    pass


class HistoricalDatasetLoader:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load_manifest(self) -> HistoricalDatasetManifest:
        path = self._root / "manifest.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HistoricalDatasetIntegrityError(
                "Unable to read valid historical dataset manifest"
            ) from exc

        required = {
            "dataset_id",
            "dataset_version",
            "schema_version",
            "market_observations_artifact",
            "financial_snapshots_artifact",
        }
        if set(payload) != required:
            raise HistoricalDatasetIntegrityError("Historical dataset manifest schema is invalid")

        market = self._artifact(payload["market_observations_artifact"])
        financial = self._artifact(payload["financial_snapshots_artifact"])
        schema_version = self._string(payload["schema_version"], "schema_version")
        if schema_version != "1":
            raise HistoricalDatasetIntegrityError(
                f"Unsupported historical dataset schema version: {schema_version}"
            )

        manifest = HistoricalDatasetManifest(
            dataset_id=self._string(payload["dataset_id"], "dataset_id"),
            dataset_version=self._string(payload["dataset_version"], "dataset_version"),
            schema_version=schema_version,
            market_observations=market,
            financial_snapshots=financial,
        )
        self._verify_artifact(manifest.market_observations)
        self._verify_artifact(manifest.financial_snapshots)
        return manifest

    def load_market_observations(self) -> list[HistoricalMarketObservation]:
        manifest = self.load_manifest()
        path = self._root / manifest.market_observations.path
        rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
        if len(rows) != manifest.market_observations.row_count:
            raise HistoricalDatasetIntegrityError("Market artifact row count mismatch")
        required = {
            "stock_id", "timeframe", "timestamp", "open", "high", "low",
            "close", "volume", "source",
        }
        observations: list[HistoricalMarketObservation] = []
        seen: set[tuple[UUID, str, datetime]] = set()
        for row in rows:
            if set(row) != required:
                raise HistoricalDatasetIntegrityError("Market artifact schema is invalid")
            try:
                item = HistoricalMarketObservation(
                    stock_id=UUID(row["stock_id"]),
                    timeframe=row["timeframe"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    open=Decimal(row["open"]),
                    high=Decimal(row["high"]),
                    low=Decimal(row["low"]),
                    close=Decimal(row["close"]),
                    volume=Decimal(row["volume"]),
                    source=row["source"],
                )
            except (ValueError, InvalidOperation) as exc:
                raise HistoricalDatasetIntegrityError("Invalid market observation") from exc
            if item.timestamp.tzinfo is None or item.timestamp.utcoffset() is None:
                raise HistoricalDatasetIntegrityError("Market timestamp must be timezone-aware")
            key = (item.stock_id, item.timeframe, item.timestamp)
            if key in seen:
                raise HistoricalDatasetIntegrityError("Duplicate market observation")
            seen.add(key)
            observations.append(item)

        if observations != sorted(
            observations, key=lambda x: (str(x.stock_id), x.timeframe, x.timestamp)
        ):
            raise HistoricalDatasetIntegrityError("Market observations are not deterministically ordered")
        return observations

    def load_financial_snapshots(self) -> list[HistoricalFinancialSnapshotRecord]:
        manifest = self.load_manifest()
        path = self._root / manifest.financial_snapshots.path
        rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
        if len(rows) != manifest.financial_snapshots.row_count:
            raise HistoricalDatasetIntegrityError("Financial artifact row count mismatch")
        required = {
            "stock_id", "period_end", "available_at", "revenue", "net_income",
            "current_assets", "current_liabilities", "source", "revision",
        }
        snapshots: list[HistoricalFinancialSnapshotRecord] = []
        for row in rows:
            if set(row) != required:
                raise HistoricalDatasetIntegrityError("Financial artifact schema is invalid")
            try:
                item = HistoricalFinancialSnapshotRecord(
                    stock_id=UUID(row["stock_id"]),
                    period_end=date.fromisoformat(row["period_end"]),
                    available_at=date.fromisoformat(row["available_at"]),
                    revenue=Decimal(row["revenue"]),
                    net_income=Decimal(row["net_income"]),
                    current_assets=self._optional_decimal(row["current_assets"]),
                    current_liabilities=self._optional_decimal(row["current_liabilities"]),
                    source=row["source"],
                    revision=row["revision"],
                )
            except (ValueError, InvalidOperation) as exc:
                raise HistoricalDatasetIntegrityError("Invalid financial snapshot") from exc
            if item.available_at < item.period_end:
                raise HistoricalDatasetIntegrityError(
                    "Financial snapshot available_at cannot precede period_end"
                )
            snapshots.append(item)

        if snapshots != sorted(
            snapshots,
            key=lambda x: (str(x.stock_id), x.period_end, x.available_at, x.revision),
        ):
            raise HistoricalDatasetIntegrityError(
                "Financial snapshots are not deterministically ordered"
            )
        return snapshots

    def _verify_artifact(self, artifact: DatasetArtifact) -> None:
        relative_path = artifact.path
        if relative_path.is_absolute() or any(part == ".." for part in relative_path.parts):
            raise HistoricalDatasetIntegrityError("Artifact path must stay inside dataset root")

        expected_paths = {"market_observations.csv", "financial_snapshots.csv"}
        if relative_path.as_posix() not in expected_paths:
            raise HistoricalDatasetIntegrityError("Artifact path is not allowed by dataset schema")

        path = self._root / relative_path
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise HistoricalDatasetIntegrityError("Unable to read dataset artifact") from exc
        if digest != artifact.sha256:
            raise HistoricalDatasetIntegrityError(
                f"Dataset artifact checksum mismatch: {artifact.path}"
            )

    @staticmethod
    def _artifact(value: object) -> DatasetArtifact:
        if not isinstance(value, dict) or set(value) != {"path", "sha256", "row_count", "coverage"}:
            raise HistoricalDatasetIntegrityError("Dataset artifact manifest entry is invalid")
        coverage_value = value["coverage"]
        if not isinstance(coverage_value, dict) or set(coverage_value) != {"start", "end", "stock_count"}:
            raise HistoricalDatasetIntegrityError("Dataset artifact coverage metadata is invalid")
        try:
            row_count = int(value["row_count"])
            stock_count = int(coverage_value["stock_count"])
        except (TypeError, ValueError) as exc:
            raise HistoricalDatasetIntegrityError("Dataset artifact counts must be integers") from exc
        if row_count < 0 or stock_count < 0:
            raise HistoricalDatasetIntegrityError("Dataset artifact counts cannot be negative")
        sha256 = HistoricalDatasetLoader._string(value["sha256"], "sha256").lower()
        if re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
            raise HistoricalDatasetIntegrityError("sha256 must be a 64-character hexadecimal digest")
        return DatasetArtifact(
            path=Path(HistoricalDatasetLoader._string(value["path"], "path")),
            sha256=sha256,
            row_count=row_count,
            coverage=DatasetCoverage(
                start=HistoricalDatasetLoader._string(coverage_value["start"], "coverage.start"),
                end=HistoricalDatasetLoader._string(coverage_value["end"], "coverage.end"),
                stock_count=stock_count,
            ),
        )

    @staticmethod
    def _string(value: object, field: str) -> str:
        if not isinstance(value, str) or not value:
            raise HistoricalDatasetIntegrityError(f"{field} must be a non-empty string")
        return value

    @staticmethod
    def _optional_decimal(value: str) -> Decimal | None:
        return Decimal(value) if value else None
