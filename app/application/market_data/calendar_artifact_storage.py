from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
from typing import Protocol


class CalendarArtifactIntegrityError(RuntimeError):
    """Raised when stored artifact bytes differ from their expected digest."""


class CalendarArtifactStore(Protocol):
    """Byte-storage port. Implementations must return stable opaque references."""

    def put(self, content: bytes) -> str: ...

    def get(self, storage_reference: str) -> bytes: ...


@dataclass(frozen=True)
class CalendarArtifactReceipt:
    """Application-level proof that stored bytes were read back and verified."""

    storage_reference: str
    sha256: str
    size_bytes: int


class CalendarArtifactService:
    """Computes artifact digests and verifies the exact bytes after storage."""

    def __init__(self, store: CalendarArtifactStore) -> None:
        self._store = store

    def archive(self, content: bytes) -> CalendarArtifactReceipt:
        if not isinstance(content, bytes) or not content:
            raise ValueError("Calendar artifact content must be non-empty bytes")

        expected_digest = hashlib.sha256(content).hexdigest()
        storage_reference = self._store.put(content)
        if not isinstance(storage_reference, str) or not storage_reference.strip():
            raise CalendarArtifactIntegrityError(
                "Artifact store returned an empty storage reference"
            )

        persisted_content = self._store.get(storage_reference)
        actual_digest = hashlib.sha256(persisted_content).hexdigest()
        if not hmac.compare_digest(expected_digest, actual_digest):
            raise CalendarArtifactIntegrityError(
                "Stored calendar artifact bytes failed read-back SHA-256 verification"
            )

        return CalendarArtifactReceipt(
            storage_reference=storage_reference,
            sha256=expected_digest,
            size_bytes=len(content),
        )
