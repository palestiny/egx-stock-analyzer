from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import re
from typing import Protocol


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


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
    """Computes artifact digests and verifies exact bytes at storage boundaries."""

    def __init__(
        self,
        store: CalendarArtifactStore,
        *,
        max_artifact_bytes: int = 20 * 1024 * 1024,
    ) -> None:
        if max_artifact_bytes <= 0:
            raise ValueError("max_artifact_bytes must be positive")
        self._store = store
        self.max_artifact_bytes = max_artifact_bytes

    def archive(self, content: bytes) -> CalendarArtifactReceipt:
        if not isinstance(content, bytes) or not content:
            raise ValueError("Calendar artifact content must be non-empty bytes")
        if len(content) > self.max_artifact_bytes:
            raise ValueError("Calendar artifact exceeds the configured size limit")

        expected_digest = hashlib.sha256(content).hexdigest()
        storage_reference = self._store.put(content)
        if not isinstance(storage_reference, str) or not storage_reference.strip():
            raise CalendarArtifactIntegrityError(
                "Artifact store returned an empty storage reference"
            )

        return self.verify(storage_reference, expected_digest)

    def verify(
        self,
        storage_reference: str,
        expected_sha256: str,
    ) -> CalendarArtifactReceipt:
        if not isinstance(storage_reference, str) or not storage_reference.strip():
            raise ValueError("Calendar artifact storage reference must be non-empty")
        if not isinstance(expected_sha256, str) or not _SHA256_PATTERN.fullmatch(expected_sha256):
            raise ValueError("Expected artifact SHA-256 must be a lowercase 64-character digest")

        persisted_content = self._store.get(storage_reference)
        if not isinstance(persisted_content, bytes) or not persisted_content:
            raise CalendarArtifactIntegrityError(
                "Stored calendar artifact is empty or is not a byte payload"
            )
        actual_digest = hashlib.sha256(persisted_content).hexdigest()
        if not hmac.compare_digest(expected_sha256, actual_digest):
            raise CalendarArtifactIntegrityError(
                "Stored calendar artifact bytes failed SHA-256 verification"
            )
        if len(persisted_content) > self.max_artifact_bytes:
            raise CalendarArtifactIntegrityError(
                "Stored calendar artifact exceeds the configured size limit"
            )

        return CalendarArtifactReceipt(
            storage_reference=storage_reference,
            sha256=actual_digest,
            size_bytes=len(persisted_content),
        )
