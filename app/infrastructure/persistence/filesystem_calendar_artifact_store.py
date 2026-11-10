from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
import re
import tempfile

from app.application.market_data.calendar_artifact_storage import (
    CalendarArtifactIntegrityError,
)


_REFERENCE_PATTERN = re.compile(r"^sha256:([0-9a-f]{64})$")


class FileSystemCalendarArtifactStore:
    """Content-addressed filesystem adapter with atomic, no-overwrite writes."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def put(self, content: bytes) -> str:
        if not isinstance(content, bytes) or not content:
            raise ValueError("Calendar artifact content must be non-empty bytes")

        digest = hashlib.sha256(content).hexdigest()
        directory = self._root / digest[:2]
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / digest

        if destination.exists() or destination.is_symlink():
            self._read_verified(destination, digest)
            return f"sha256:{digest}"

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=directory,
                prefix=".calendar-artifact-",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())

            try:
                os.link(temporary_path, destination)
            except FileExistsError:
                self._read_verified(destination, digest)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

        self._read_verified(destination, digest)
        return f"sha256:{digest}"

    def get(self, storage_reference: str) -> bytes:
        match = _REFERENCE_PATTERN.fullmatch(storage_reference)
        if match is None:
            raise ValueError("Invalid calendar artifact storage reference")
        digest = match.group(1)
        path = self._root / digest[:2] / digest
        return self._read_verified(path, digest)

    @staticmethod
    def _read_verified(path: Path, expected_digest: str) -> bytes:
        if path.is_symlink():
            raise CalendarArtifactIntegrityError(
                "Calendar artifact storage path must not be a symbolic link"
            )
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            raise
        actual_digest = hashlib.sha256(content).hexdigest()
        if not hmac.compare_digest(expected_digest, actual_digest):
            raise CalendarArtifactIntegrityError(
                "Stored calendar artifact bytes failed SHA-256 verification"
            )
        return content
