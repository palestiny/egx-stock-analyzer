from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat


_STORAGE_REFERENCE_PATTERN = re.compile(r"^sha256:([0-9a-f]{64})$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_DIRECTORY_PATTERN = re.compile(r"^[0-9a-f]{2}$")


class CalendarArtifactInventoryStatus(StrEnum):
    REFERENCED_AND_VALID = "REFERENCED_AND_VALID"
    ORPHANED = "ORPHANED"
    MISSING = "MISSING"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"
    INVALID_REFERENCE = "INVALID_REFERENCE"
    INVALID_STORAGE_ENTRY = "INVALID_STORAGE_ENTRY"


@dataclass(frozen=True)
class CalendarArtifactInventoryEntry:
    status: CalendarArtifactInventoryStatus
    storage_reference: str | None
    evidence_count: int
    size_bytes: int | None
    detail: str


@dataclass(frozen=True)
class CalendarArtifactInventoryReport:
    database_path: str
    storage_root: str
    entries: tuple[CalendarArtifactInventoryEntry, ...]

    @property
    def counts(self) -> dict[str, int]:
        return {
            status.value: sum(entry.status is status for entry in self.entries)
            for status in CalendarArtifactInventoryStatus
        }

    @property
    def is_clean(self) -> bool:
        return all(
            entry.status is CalendarArtifactInventoryStatus.REFERENCED_AND_VALID
            for entry in self.entries
        )

    @property
    def exit_code(self) -> int:
        return 0 if self.is_clean else 1

    def to_dict(self) -> dict:
        return {
            "database_path": self.database_path,
            "storage_root": self.storage_root,
            "is_clean": self.is_clean,
            "counts": self.counts,
            "entries": [
                {
                    "status": entry.status.value,
                    "storage_reference": entry.storage_reference,
                    "evidence_count": entry.evidence_count,
                    "size_bytes": entry.size_bytes,
                    "detail": entry.detail,
                }
                for entry in self.entries
            ],
        }


def _read_archived_references(database_path: Path) -> list[tuple[str | None, str | None]]:
    if not database_path.is_file():
        raise FileNotFoundError(f"Calendar evidence database does not exist: {database_path}")

    # Do not use connect_sqlite(): its normal connection setup may change journal mode.
    # mode=ro and query_only make this inventory strictly read-only at the SQLite layer.
    database_uri = f"{database_path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(database_uri, uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        rows = connection.execute(
            """
            SELECT artifact_storage_reference, artifact_sha256
            FROM egx_calendar_evidence
            WHERE artifact_retention = 'ARCHIVED'
            ORDER BY artifact_storage_reference, evidence_id
            """
        ).fetchall()
        return [(row[0], row[1]) for row in rows]
    finally:
        connection.close()


def _digest_regular_file(path: Path) -> tuple[str, int]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("Storage entry is not a regular file")
        digest = hashlib.sha256()
        size_bytes = 0
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
                size_bytes += len(chunk)
        return digest.hexdigest(), size_bytes
    finally:
        os.close(descriptor)


def _scan_storage_root(
    storage_root: Path,
) -> tuple[dict[str, tuple[str, int]], list[CalendarArtifactInventoryEntry]]:
    if storage_root.is_symlink():
        raise ValueError("Calendar artifact storage root must not be a symbolic link")
    if not storage_root.is_dir():
        raise FileNotFoundError(
            f"Calendar artifact storage root does not exist or is not a directory: {storage_root}"
        )

    valid_files: dict[str, tuple[str, int]] = {}
    invalid_entries: list[CalendarArtifactInventoryEntry] = []

    def invalid(path: Path, detail: str) -> None:
        invalid_entries.append(
            CalendarArtifactInventoryEntry(
                status=CalendarArtifactInventoryStatus.INVALID_STORAGE_ENTRY,
                storage_reference=None,
                evidence_count=0,
                size_bytes=None,
                detail=f"{path.relative_to(storage_root)}: {detail}",
            )
        )

    with os.scandir(storage_root) as root_entries:
        for directory_entry in root_entries:
            directory_path = Path(directory_entry.path)
            if directory_entry.is_symlink():
                invalid(directory_path, "symbolic links are not followed")
                continue
            if not directory_entry.is_dir(follow_symlinks=False):
                invalid(directory_path, "unexpected entry at storage-root level")
                continue
            prefix = directory_entry.name
            if _DIRECTORY_PATTERN.fullmatch(prefix) is None:
                invalid(directory_path, "content-addressed directory must be a two-character lowercase hex prefix")
                continue

            try:
                with os.scandir(directory_path) as artifact_entries:
                    for artifact_entry in artifact_entries:
                        artifact_path = Path(artifact_entry.path)
                        if artifact_entry.is_symlink():
                            invalid(artifact_path, "symbolic links are not followed")
                            continue
                        if artifact_entry.is_dir(follow_symlinks=False):
                            invalid(artifact_path, "nested directories are not valid artifact entries")
                            continue
                        if not artifact_entry.is_file(follow_symlinks=False):
                            invalid(artifact_path, "entry is not a regular file")
                            continue
                        digest_name = artifact_entry.name
                        if (
                            _DIGEST_PATTERN.fullmatch(digest_name) is None
                            or not digest_name.startswith(prefix)
                        ):
                            invalid(artifact_path, "filename does not match the content-addressed layout")
                            continue
                        try:
                            actual_digest, size_bytes = _digest_regular_file(artifact_path)
                        except (OSError, ValueError) as error:
                            invalid(artifact_path, f"cannot safely read artifact ({type(error).__name__})")
                            continue
                        valid_files[digest_name] = (actual_digest, size_bytes)
            except OSError as error:
                invalid(directory_path, f"cannot scan directory ({type(error).__name__})")

    return valid_files, invalid_entries


def run_calendar_artifact_inventory(
    database_path: str | Path,
    storage_root: str | Path,
) -> CalendarArtifactInventoryReport:
    """Compare ARCHIVED database references with stored bytes without mutating either."""
    database = Path(database_path).expanduser()
    root = Path(storage_root).expanduser()
    if database.is_symlink():
        raise ValueError("Calendar evidence database path must not be a symbolic link")

    archived_rows = _read_archived_references(database)
    referenced: dict[str, list[str | None]] = {}
    entries: list[CalendarArtifactInventoryEntry] = []

    for storage_reference, expected_digest in archived_rows:
        if not isinstance(storage_reference, str):
            entries.append(
                CalendarArtifactInventoryEntry(
                    status=CalendarArtifactInventoryStatus.INVALID_REFERENCE,
                    storage_reference=None,
                    evidence_count=1,
                    size_bytes=None,
                    detail="ARCHIVED evidence has no storage reference",
                )
            )
            continue
        match = _STORAGE_REFERENCE_PATTERN.fullmatch(storage_reference)
        if match is None:
            entries.append(
                CalendarArtifactInventoryEntry(
                    status=CalendarArtifactInventoryStatus.INVALID_REFERENCE,
                    storage_reference=storage_reference,
                    evidence_count=1,
                    size_bytes=None,
                    detail="ARCHIVED evidence has a malformed storage reference",
                )
            )
            continue
        referenced.setdefault(storage_reference, []).append(expected_digest)

    files, invalid_entries = _scan_storage_root(root)
    entries.extend(invalid_entries)

    for storage_reference, expected_digests in sorted(referenced.items()):
        digest = storage_reference.removeprefix("sha256:")
        stored = files.pop(digest, None)
        if any(value != digest for value in expected_digests):
            entries.append(
                CalendarArtifactInventoryEntry(
                    status=CalendarArtifactInventoryStatus.INTEGRITY_FAILURE,
                    storage_reference=storage_reference,
                    evidence_count=len(expected_digests),
                    size_bytes=stored[1] if stored is not None else None,
                    detail="Database artifact_sha256 metadata does not consistently match the content-addressed reference",
                )
            )
            continue

        if stored is None:
            entries.append(
                CalendarArtifactInventoryEntry(
                    status=CalendarArtifactInventoryStatus.MISSING,
                    storage_reference=storage_reference,
                    evidence_count=len(expected_digests),
                    size_bytes=None,
                    detail="Database references an artifact that is absent from storage",
                )
            )
            continue

        actual_digest, size_bytes = stored
        if actual_digest != digest:
            entries.append(
                CalendarArtifactInventoryEntry(
                    status=CalendarArtifactInventoryStatus.INTEGRITY_FAILURE,
                    storage_reference=storage_reference,
                    evidence_count=len(expected_digests),
                    size_bytes=size_bytes,
                    detail="Stored bytes do not match the content-addressed filename",
                )
            )
            continue

        entries.append(
            CalendarArtifactInventoryEntry(
                status=CalendarArtifactInventoryStatus.REFERENCED_AND_VALID,
                storage_reference=storage_reference,
                evidence_count=len(expected_digests),
                size_bytes=size_bytes,
                detail="Stored bytes match the database digest and content-addressed reference",
            )
        )

    for digest, (actual_digest, size_bytes) in sorted(files.items()):
        if actual_digest != digest:
            entries.append(
                CalendarArtifactInventoryEntry(
                    status=CalendarArtifactInventoryStatus.INTEGRITY_FAILURE,
                    storage_reference=f"sha256:{digest}",
                    evidence_count=0,
                    size_bytes=size_bytes,
                    detail="Unreferenced stored bytes do not match their content-addressed filename",
                )
            )
        else:
            entries.append(
                CalendarArtifactInventoryEntry(
                    status=CalendarArtifactInventoryStatus.ORPHANED,
                    storage_reference=f"sha256:{digest}",
                    evidence_count=0,
                    size_bytes=size_bytes,
                    detail="Valid content-addressed artifact has no ARCHIVED evidence reference",
                )
            )

    entries.sort(
        key=lambda item: (
            item.status.value,
            item.storage_reference or "",
            item.detail,
        )
    )
    return CalendarArtifactInventoryReport(
        database_path=str(database.resolve()),
        storage_root=str(root.resolve()),
        entries=tuple(entries),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only audit of archived EGX calendar evidence artifacts."
    )
    parser.add_argument("--database", required=True, help="SQLite analysis database path.")
    parser.add_argument("--storage-root", required=True, help="Calendar artifact storage directory.")
    args = parser.parse_args()

    try:
        report = run_calendar_artifact_inventory(args.database, args.storage_root)
    except Exception as error:
        print(json.dumps({
            "status": "FAILED",
            "error_type": type(error).__name__,
            "error": str(error),
        }, indent=2))
        return 2

    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
