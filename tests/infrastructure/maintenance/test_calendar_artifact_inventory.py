import hashlib
import sqlite3
from pathlib import Path

import pytest

from app.infrastructure.maintenance.calendar_artifact_inventory import (
    CalendarArtifactInventoryStatus as Status,
    run_calendar_artifact_inventory,
)


def create_database(path: Path, records=()) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE egx_calendar_evidence (
                evidence_id TEXT PRIMARY KEY,
                artifact_retention TEXT,
                artifact_storage_reference TEXT,
                artifact_sha256 TEXT
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO egx_calendar_evidence (
                evidence_id, artifact_retention,
                artifact_storage_reference, artifact_sha256
            ) VALUES (?, ?, ?, ?)
            """,
            records,
        )


def store_bytes(root: Path, content: bytes, *, filename_digest: str | None = None) -> str:
    digest = hashlib.sha256(content).hexdigest()
    name = filename_digest or digest
    directory = root / name[:2]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(content)
    return f"sha256:{name}"


def statuses(report):
    return [entry.status for entry in report.entries]


def test_inventory_reports_referenced_bytes_as_valid_and_counts_evidence(tmp_path):
    database = tmp_path / "analysis.db"
    root = tmp_path / "artifacts"
    root.mkdir()
    content = b"verified calendar notice"
    reference = store_bytes(root, content)
    digest = hashlib.sha256(content).hexdigest()
    create_database(
        database,
        [
            ("evidence-1", "ARCHIVED", reference, digest),
            ("evidence-2", "ARCHIVED", reference, digest),
        ],
    )

    report = run_calendar_artifact_inventory(database, root)

    assert report.is_clean is True
    assert report.exit_code == 0
    assert report.counts[Status.REFERENCED_AND_VALID.value] == 1
    entry = report.entries[0]
    assert entry.evidence_count == 2
    assert entry.size_bytes == len(content)


def test_inventory_reports_missing_referenced_artifact(tmp_path):
    database = tmp_path / "analysis.db"
    root = tmp_path / "artifacts"
    root.mkdir()
    digest = "a" * 64
    create_database(database, [("evidence-1", "ARCHIVED", f"sha256:{digest}", digest)])

    report = run_calendar_artifact_inventory(database, root)

    assert statuses(report) == [Status.MISSING]
    assert report.exit_code == 1


def test_inventory_reports_orphaned_valid_artifact(tmp_path):
    database = tmp_path / "analysis.db"
    root = tmp_path / "artifacts"
    root.mkdir()
    store_bytes(root, b"uploaded but never published")
    create_database(database)

    report = run_calendar_artifact_inventory(database, root)

    assert statuses(report) == [Status.ORPHANED]
    assert report.entries[0].evidence_count == 0


def test_inventory_detects_tampered_referenced_bytes(tmp_path):
    database = tmp_path / "analysis.db"
    root = tmp_path / "artifacts"
    root.mkdir()
    original = b"original bytes"
    reference = store_bytes(root, original)
    digest = hashlib.sha256(original).hexdigest()
    path = root / digest[:2] / digest
    path.write_bytes(b"tampered bytes")
    create_database(database, [("evidence-1", "ARCHIVED", reference, digest)])

    report = run_calendar_artifact_inventory(database, root)

    assert statuses(report) == [Status.INTEGRITY_FAILURE]
    assert report.entries[0].size_bytes == len(b"tampered bytes")


def test_inventory_detects_database_digest_mismatch(tmp_path):
    database = tmp_path / "analysis.db"
    root = tmp_path / "artifacts"
    root.mkdir()
    content = b"stored bytes"
    reference = store_bytes(root, content)
    create_database(database, [("evidence-1", "ARCHIVED", reference, "b" * 64)])

    report = run_calendar_artifact_inventory(database, root)

    assert statuses(report) == [Status.INTEGRITY_FAILURE]
    assert "database artifact_sha256" in report.entries[0].detail


@pytest.mark.parametrize("reference", [None, "../outside", "sha256:ABC"])
def test_inventory_reports_invalid_database_references(tmp_path, reference):
    database = tmp_path / "analysis.db"
    root = tmp_path / "artifacts"
    root.mkdir()
    create_database(database, [("evidence-1", "ARCHIVED", reference, "a" * 64)])

    report = run_calendar_artifact_inventory(database, root)

    assert statuses(report) == [Status.INVALID_REFERENCE]
    assert report.exit_code == 1


def test_inventory_ignores_external_only_evidence(tmp_path):
    database = tmp_path / "analysis.db"
    root = tmp_path / "artifacts"
    root.mkdir()
    create_database(
        database,
        [("evidence-1", "EXTERNAL_ONLY", None, "a" * 64)],
    )

    report = run_calendar_artifact_inventory(database, root)

    assert report.is_clean is True
    assert report.entries == ()


def test_inventory_reports_unexpected_entries_without_following_symlinks(tmp_path):
    database = tmp_path / "analysis.db"
    root = tmp_path / "artifacts"
    root.mkdir()
    create_database(database)
    (root / "unexpected.txt").write_text("not an artifact")
    target = tmp_path / "outside"
    target.mkdir()
    (target / "secret").write_text("outside")
    try:
        (root / "ab").symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Directory symlinks are unavailable on this platform")

    report = run_calendar_artifact_inventory(database, root)

    assert report.counts[Status.INVALID_STORAGE_ENTRY.value] == 2
    assert all(entry.status is Status.INVALID_STORAGE_ENTRY for entry in report.entries)


def test_inventory_does_not_modify_database_or_storage(tmp_path):
    database = tmp_path / "analysis.db"
    root = tmp_path / "artifacts"
    root.mkdir()
    content = b"read only"
    reference = store_bytes(root, content)
    digest = hashlib.sha256(content).hexdigest()
    create_database(database, [("evidence-1", "ARCHIVED", reference, digest)])
    database_mtime = database.stat().st_mtime_ns
    artifact = root / digest[:2] / digest
    artifact_mtime = artifact.stat().st_mtime_ns

    report = run_calendar_artifact_inventory(database, root)

    assert report.is_clean is True
    assert database.stat().st_mtime_ns == database_mtime
    assert artifact.stat().st_mtime_ns == artifact_mtime


def test_inventory_fails_without_creating_missing_storage_root(tmp_path):
    database = tmp_path / "analysis.db"
    root = tmp_path / "missing-artifacts"
    create_database(database)

    with pytest.raises(FileNotFoundError, match="storage root"):
        run_calendar_artifact_inventory(database, root)

    assert not root.exists()


def test_inventory_rejects_symlinked_storage_root(tmp_path):
    database = tmp_path / "analysis.db"
    real_root = tmp_path / "real-artifacts"
    real_root.mkdir()
    root_link = tmp_path / "artifact-link"
    create_database(database)
    try:
        root_link.symlink_to(real_root, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Directory symlinks are unavailable on this platform")

    with pytest.raises(ValueError, match="storage root"):
        run_calendar_artifact_inventory(database, root_link)
