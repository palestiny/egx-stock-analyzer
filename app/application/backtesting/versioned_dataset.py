from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class DatasetManifestError(ValueError):
    """Raised when a versioned historical dataset manifest is invalid."""


class DatasetIntegrityError(ValueError):
    """Raised when dataset bytes do not match the pinned manifest hash."""


@dataclass(frozen=True)
class VersionedDatasetManifest:
    """Immutable identity and coverage contract for a historical dataset artifact.

    The physical artifact format is deliberately outside this contract. The manifest
    describes how an artifact is identified, located, covered, and verified.
    """

    dataset_id: str
    version: str
    schema_version: str
    artifact_uri: str
    sha256: str
    coverage_start: date
    coverage_end: date
    provenance: dict[str, Any]

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "VersionedDatasetManifest":
        required = (
            "dataset_id",
            "version",
            "schema_version",
            "artifact_uri",
            "sha256",
            "coverage_start",
            "coverage_end",
            "provenance",
        )
        missing = [key for key in required if key not in payload]
        if missing:
            raise DatasetManifestError(
                f"Missing required manifest fields: {', '.join(missing)}"
            )

        try:
            dataset_id = cls._required_text(payload["dataset_id"], "dataset_id")
            version = cls._required_text(payload["version"], "version")
            schema_version = cls._required_text(
                payload["schema_version"], "schema_version"
            )
            artifact_uri = cls._required_text(payload["artifact_uri"], "artifact_uri")
            sha256 = cls._required_text(payload["sha256"], "sha256").lower()
            coverage_start = cls._parse_date(payload["coverage_start"], "coverage_start")
            coverage_end = cls._parse_date(payload["coverage_end"], "coverage_end")
            provenance = cls._parse_provenance(payload["provenance"])
        except (TypeError, ValueError) as exc:
            if isinstance(exc, DatasetManifestError):
                raise
            raise DatasetManifestError(str(exc)) from exc

        if not _SHA256_PATTERN.fullmatch(sha256):
            raise DatasetManifestError("sha256 must be a 64-character lowercase hex digest")

        if coverage_start > coverage_end:
            raise DatasetManifestError("coverage_start must not be after coverage_end")

        return cls(
            dataset_id=dataset_id,
            version=version,
            schema_version=schema_version,
            artifact_uri=artifact_uri,
            sha256=sha256,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            provenance=provenance,
        )

    @classmethod
    def from_json(cls, payload: str) -> "VersionedDatasetManifest":
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise DatasetManifestError("Manifest must contain valid JSON") from exc

        if not isinstance(value, dict):
            raise DatasetManifestError("Manifest JSON root must be an object")

        return cls.from_dict(value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "schema_version": self.schema_version,
            "artifact_uri": self.artifact_uri,
            "sha256": self.sha256,
            "coverage_start": self.coverage_start.isoformat(),
            "coverage_end": self.coverage_end.isoformat(),
            "provenance": dict(self.provenance),
        }

    def covers(self, from_date: date, to_date: date) -> bool:
        if from_date > to_date:
            raise ValueError("from_date must not be after to_date")
        return (
            self.coverage_start <= from_date
            and to_date <= self.coverage_end
        )

    def verify_integrity(self, artifact: bytes) -> None:
        actual = hashlib.sha256(artifact).hexdigest()
        if actual != self.sha256:
            raise DatasetIntegrityError(
                "Dataset artifact integrity mismatch: "
                f"expected={self.sha256}, actual={actual}"
            )

    @staticmethod
    def _required_text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise DatasetManifestError(f"{field} must be a non-empty string")
        return value

    @staticmethod
    def _parse_date(value: Any, field: str) -> date:
        if not isinstance(value, str):
            raise DatasetManifestError(f"{field} must be an ISO date string")
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise DatasetManifestError(
                f"{field} must be a valid ISO date"
            ) from exc

    @staticmethod
    def _parse_provenance(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict) or not value:
            raise DatasetManifestError("provenance must be a non-empty object")

        exported_at = value.get("exported_at")
        if exported_at is not None:
            if not isinstance(exported_at, str):
                raise DatasetManifestError("provenance.exported_at must be a string")
            try:
                datetime.fromisoformat(exported_at)
            except ValueError as exc:
                raise DatasetManifestError(
                    "provenance.exported_at must be a valid ISO timestamp"
                ) from exc

        return dict(value)
