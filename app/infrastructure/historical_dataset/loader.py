import csv
import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

from app.infrastructure.historical_dataset.models import (
    DatasetArtifact,
    DatasetCoverage,
    DatasetProvenance,
    HistoricalDatasetManifest,
    HistoricalFinancialSnapshotRecord,
    HistoricalMarketObservation,
    RawSourceEvidence,
)


EGX_TIMEZONE = ZoneInfo("Africa/Cairo")


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
        if schema_version != "3":
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
        seen_daily_sessions: set[tuple[UUID, str, date]] = set()
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
            if not item.timeframe.strip():
                raise HistoricalDatasetIntegrityError("Market observation timeframe cannot be empty")
            if not item.source.strip():
                raise HistoricalDatasetIntegrityError("Market observation source cannot be empty")
            market_values = (item.open, item.high, item.low, item.close, item.volume)
            if any(not value.is_finite() for value in market_values):
                raise HistoricalDatasetIntegrityError("Market OHLCV values must be finite")
            if any(value <= 0 for value in (item.open, item.high, item.low, item.close)):
                raise HistoricalDatasetIntegrityError("Market prices must be positive")
            if item.volume < 0:
                raise HistoricalDatasetIntegrityError("Market volume cannot be negative")
            if (
                item.low > item.high
                or item.low > item.open
                or item.low > item.close
                or item.high < item.open
                or item.high < item.close
            ):
                raise HistoricalDatasetIntegrityError("Market OHLC values are inconsistent")
            key = (item.stock_id, item.timeframe, item.timestamp)
            if key in seen:
                raise HistoricalDatasetIntegrityError("Duplicate market observation")
            seen.add(key)
            if item.timeframe == "1d":
                session_key = (
                    item.stock_id,
                    item.timeframe,
                    item.timestamp.astimezone(EGX_TIMEZONE).date(),
                )
                if session_key in seen_daily_sessions:
                    raise HistoricalDatasetIntegrityError(
                        "Duplicate daily market session in Cairo timezone"
                    )
                seen_daily_sessions.add(session_key)
            observations.append(item)

        if observations != sorted(
            observations, key=lambda x: (str(x.stock_id), x.timeframe, x.timestamp)
        ):
            raise HistoricalDatasetIntegrityError("Market observations are not deterministically ordered")
        self._validate_coverage(
            observations,
            manifest.market_observations.coverage,
            lambda item: item.timestamp,
        )
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
            financial_values = (
                item.revenue,
                item.net_income,
                item.current_assets,
                item.current_liabilities,
            )
            if any(value is not None and not value.is_finite() for value in financial_values):
                raise HistoricalDatasetIntegrityError("Financial snapshot values must be finite")
            if item.available_at < item.period_end:
                raise HistoricalDatasetIntegrityError(
                    "Financial snapshot available_at cannot precede period_end"
                )
            if not item.source.strip():
                raise HistoricalDatasetIntegrityError("Financial snapshot source cannot be empty")
            if not item.revision.strip():
                raise HistoricalDatasetIntegrityError("Financial snapshot revision cannot be empty")
            snapshots.append(item)

        same_time_keys = [
            (item.stock_id, item.period_end, item.available_at)
            for item in snapshots
        ]
        if len(same_time_keys) != len(set(same_time_keys)):
            raise HistoricalDatasetIntegrityError(
                "Financial snapshots contain ambiguous same-time revisions"
            )

        if snapshots != sorted(
            snapshots,
            key=lambda x: (str(x.stock_id), x.period_end, x.available_at, x.revision),
        ):
            raise HistoricalDatasetIntegrityError(
                "Financial snapshots are not deterministically ordered"
            )

        self._validate_coverage(
            snapshots,
            manifest.financial_snapshots.coverage,
            lambda item: item.period_end,
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

    def verify_raw_source_evidence(self) -> None:
        manifest = self.load_manifest()
        self._verify_raw_source_evidence(manifest.market_observations)
        self._verify_raw_source_evidence(manifest.financial_snapshots)

    def _verify_raw_source_evidence(self, artifact: DatasetArtifact) -> None:
        if artifact.provenance is None:
            raise HistoricalDatasetIntegrityError("Dataset artifact provenance is required")
        evidence = artifact.provenance.raw_source_evidence
        reference = Path(evidence.reference)
        if reference.is_absolute() or any(part == ".." for part in reference.parts):
            raise HistoricalDatasetIntegrityError(
                "raw_source_evidence.reference must stay inside dataset root"
            )
        path = self._root / reference
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise HistoricalDatasetIntegrityError(
                "Unable to read preserved raw-source evidence"
            ) from exc
        if digest != evidence.sha256:
            raise HistoricalDatasetIntegrityError(
                "Raw-source evidence checksum mismatch"
            )

    @staticmethod
    def _validate_coverage(items: list, coverage: DatasetCoverage, key) -> None:
        if not items:
            if coverage.stock_count != 0:
                raise HistoricalDatasetIntegrityError(
                    "Dataset coverage stock count mismatch"
                )
            return

        actual_values = [key(item) for item in items]
        expected_start = HistoricalDatasetLoader._parse_coverage_value(coverage.start)
        expected_end = HistoricalDatasetLoader._parse_coverage_value(coverage.end)

        if min(actual_values) != expected_start or max(actual_values) != expected_end:
            raise HistoricalDatasetIntegrityError("Dataset coverage range mismatch")

        actual_stock_count = len({item.stock_id for item in items})
        if actual_stock_count != coverage.stock_count:
            raise HistoricalDatasetIntegrityError(
                "Dataset coverage stock count mismatch"
            )

    @staticmethod
    def _parse_coverage_value(value: str):
        try:
            return datetime.fromisoformat(value) if "T" in value else date.fromisoformat(value)
        except ValueError as exc:
            raise HistoricalDatasetIntegrityError(
                "Dataset coverage range is invalid"
            ) from exc

    @staticmethod
    def _artifact(value: object) -> DatasetArtifact:
        if not isinstance(value, dict) or set(value) != {
            "path", "sha256", "row_count", "coverage", "provenance"
        }:
            raise HistoricalDatasetIntegrityError("Dataset artifact manifest entry is invalid")
        coverage_value = value["coverage"]
        if not isinstance(coverage_value, dict) or set(coverage_value) != {
            "start", "end", "stock_count"
        }:
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
            provenance=HistoricalDatasetLoader._provenance(value["provenance"]),
        )

    @staticmethod
    def _provenance(value: object) -> DatasetProvenance:
        if not isinstance(value, dict) or set(value) != {
            "provider",
            "source_url",
            "acquired_at",
            "symbol_mappings",
            "corporate_action_convention",
            "missing_data_findings",
            "exclusions",
            "licensing_notes",
            "transformation_manifest",
            "raw_source_evidence",
        }:
            raise HistoricalDatasetIntegrityError("Dataset provenance metadata is invalid")

        provider = HistoricalDatasetLoader._string(value["provider"], "provenance.provider")
        source_url = HistoricalDatasetLoader._string(value["source_url"], "provenance.source_url")
        acquired_at_raw = HistoricalDatasetLoader._string(
            value["acquired_at"], "provenance.acquired_at"
        )
        try:
            acquired_at = datetime.fromisoformat(acquired_at_raw)
        except ValueError as exc:
            raise HistoricalDatasetIntegrityError(
                "provenance.acquired_at must be ISO-8601"
            ) from exc
        if acquired_at.tzinfo is None or acquired_at.utcoffset() is None:
            raise HistoricalDatasetIntegrityError(
                "provenance.acquired_at must be timezone-aware"
            )

        mappings = HistoricalDatasetLoader._string_sequence(
            value["symbol_mappings"], "provenance.symbol_mappings"
        )
        if not mappings:
            raise HistoricalDatasetIntegrityError(
                "provenance.symbol_mappings cannot be empty"
            )

        return DatasetProvenance(
            provider=provider,
            source_url=source_url,
            acquired_at=acquired_at,
            symbol_mappings=mappings,
            corporate_action_convention=HistoricalDatasetLoader._string(
                value["corporate_action_convention"],
                "provenance.corporate_action_convention",
            ),
            missing_data_findings=HistoricalDatasetLoader._string_sequence(
                value["missing_data_findings"], "provenance.missing_data_findings"
            ),
            exclusions=HistoricalDatasetLoader._string_sequence(
                value["exclusions"], "provenance.exclusions"
            ),
            licensing_notes=HistoricalDatasetLoader._string(
                value["licensing_notes"], "provenance.licensing_notes"
            ),
            transformation_manifest=HistoricalDatasetLoader._string(
                value["transformation_manifest"], "provenance.transformation_manifest"
            ),
            raw_source_evidence=HistoricalDatasetLoader._raw_source_evidence(
                value["raw_source_evidence"]
            ),
        )

    @staticmethod
    def _raw_source_evidence(value: object) -> RawSourceEvidence:
        if not isinstance(value, dict) or set(value) != {"reference", "sha256", "retention"}:
            raise HistoricalDatasetIntegrityError(
                "provenance.raw_source_evidence metadata is invalid"
            )
        sha256 = HistoricalDatasetLoader._string(
            value["sha256"], "provenance.raw_source_evidence.sha256"
        ).lower()
        if re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
            raise HistoricalDatasetIntegrityError(
                "provenance.raw_source_evidence.sha256 must be a 64-character hexadecimal digest"
            )
        return RawSourceEvidence(
            reference=HistoricalDatasetLoader._string(
                value["reference"], "provenance.raw_source_evidence.reference"
            ),
            sha256=sha256,
            retention=HistoricalDatasetLoader._string(
                value["retention"], "provenance.raw_source_evidence.retention"
            ),
        )

    @staticmethod
    def _string_sequence(value: object, field: str) -> tuple[str, ...]:
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            raise HistoricalDatasetIntegrityError(f"{field} must be a list of non-empty strings")
        return tuple(value)

    @staticmethod
    def _string(value: object, field: str) -> str:
        if not isinstance(value, str) or not value:
            raise HistoricalDatasetIntegrityError(f"{field} must be a non-empty string")
        return value

    @staticmethod
    def _optional_decimal(value: str) -> Decimal | None:
        return Decimal(value) if value else None
