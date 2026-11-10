import hashlib

import pytest

from app.application.market_data.calendar_artifact_storage import (
    CalendarArtifactIntegrityError,
    CalendarArtifactService,
)
from app.infrastructure.persistence.filesystem_calendar_artifact_store import (
    FileSystemCalendarArtifactStore,
)


def test_archive_computes_digest_and_verifies_exact_bytes_after_readback(tmp_path):
    content = b"official EGX calendar notice\x00with binary content"
    store = FileSystemCalendarArtifactStore(tmp_path / "artifacts")

    receipt = CalendarArtifactService(store).archive(content)

    assert receipt.sha256 == hashlib.sha256(content).hexdigest()
    assert receipt.storage_reference == f"sha256:{receipt.sha256}"
    assert receipt.size_bytes == len(content)
    assert store.get(receipt.storage_reference) == content


def test_content_addressed_write_is_idempotent_for_identical_bytes(tmp_path):
    content = b"same immutable artifact"
    store = FileSystemCalendarArtifactStore(tmp_path / "artifacts")

    first = store.put(content)
    second = store.put(content)

    assert first == second
    assert store.get(first) == content


def test_read_rejects_artifact_bytes_tampered_after_storage(tmp_path):
    root = tmp_path / "artifacts"
    store = FileSystemCalendarArtifactStore(root)
    content = b"original source bytes"
    reference = store.put(content)
    digest = hashlib.sha256(content).hexdigest()
    artifact_path = root / digest[:2] / digest
    artifact_path.write_bytes(b"tampered source bytes")

    with pytest.raises(CalendarArtifactIntegrityError, match="SHA-256"):
        store.get(reference)


def test_read_rejects_missing_artifact(tmp_path):
    store = FileSystemCalendarArtifactStore(tmp_path / "artifacts")
    missing_digest = "a" * 64

    with pytest.raises(FileNotFoundError):
        store.get(f"sha256:{missing_digest}")


def test_read_rejects_malformed_storage_reference(tmp_path):
    store = FileSystemCalendarArtifactStore(tmp_path / "artifacts")

    with pytest.raises(ValueError, match="storage reference"):
        store.get("../outside")


def test_application_service_detects_store_returning_different_bytes():
    class CorruptingStore:
        def put(self, content: bytes) -> str:
            return "test-reference"

        def get(self, storage_reference: str) -> bytes:
            return b"different bytes"

    service = CalendarArtifactService(CorruptingStore())

    with pytest.raises(CalendarArtifactIntegrityError, match="read-back"):
        service.archive(b"original bytes")


def test_archive_rejects_empty_or_non_bytes_content(tmp_path):
    service = CalendarArtifactService(
        FileSystemCalendarArtifactStore(tmp_path / "artifacts")
    )

    with pytest.raises(ValueError, match="non-empty bytes"):
        service.archive(b"")

    with pytest.raises(ValueError, match="non-empty bytes"):
        service.archive("not bytes")  # type: ignore[arg-type]
