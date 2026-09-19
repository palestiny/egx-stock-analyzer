from dataclasses import dataclass
from datetime import datetime, timezone
from secrets import token_urlsafe
from typing import Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True)
class StoredCredential:
    id: UUID
    user_id: UUID
    status: str
    created_at: datetime
    revoked_at: datetime | None = None
    replaced_by: UUID | None = None


@dataclass(frozen=True)
class IssuedCredential:
    id: UUID
    user_id: UUID
    secret: str


class CredentialStore(Protocol):
    def create(
        self,
        credential: StoredCredential,
        verifier: str,
    ) -> None:
        raise NotImplementedError

    def find_active_user_id(self, secret: str) -> UUID | None:
        credential = self.find_active_credential(secret)
        return credential.user_id if credential is not None else None

    def find_active_credential(self, secret: str) -> StoredCredential | None:
        raise NotImplementedError

    def replace(
        self,
        credential_id: UUID,
        user_id: UUID,
        replacement: StoredCredential,
        replacement_verifier: str,
        revoked_at: datetime,
    ) -> None:
        raise NotImplementedError

    def revoke(
        self,
        credential_id: UUID,
        revoked_at: datetime,
        replacement_id: UUID | None = None,
    ) -> None:
        raise NotImplementedError


class CredentialService:
    def __init__(self, store: CredentialStore) -> None:
        self._store = store

    def provision(self, user_id: UUID) -> IssuedCredential:
        credential_id = uuid4()
        secret = token_urlsafe(32)
        credential = StoredCredential(
            id=credential_id,
            user_id=user_id,
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        self._store.create(credential, _derive_verifier(secret))
        return IssuedCredential(
            id=credential_id,
            user_id=user_id,
            secret=secret,
        )

    def rotate(self, credential_id: UUID, user_id: UUID) -> IssuedCredential:
        replacement_id = uuid4()
        secret = token_urlsafe(32)
        replacement = StoredCredential(
            id=replacement_id,
            user_id=user_id,
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        self._store.replace(
            credential_id=credential_id,
            user_id=user_id,
            replacement=replacement,
            replacement_verifier=_derive_verifier(secret),
            revoked_at=datetime.now(timezone.utc),
        )
        return IssuedCredential(id=replacement_id, user_id=user_id, secret=secret)

    def revoke(self, credential_id: UUID) -> None:
        self._store.revoke(
            credential_id,
            revoked_at=datetime.now(timezone.utc),
        )


def _derive_verifier(secret: str) -> str:
    import hashlib
    import os
    import base64

    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt,
        600_000,
    )
    return "pbkdf2_sha256$600000$" + base64.urlsafe_b64encode(salt).decode("ascii") + "$" + base64.urlsafe_b64encode(digest).decode("ascii")


def verify_secret(secret: str, verifier: str) -> bool:
    import base64
    import hashlib
    from secrets import compare_digest

    try:
        algorithm, raw_iterations, raw_salt, raw_digest = verifier.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(raw_iterations)
        salt = base64.urlsafe_b64decode(raw_salt.encode("ascii"))
        expected = base64.urlsafe_b64decode(raw_digest.encode("ascii"))
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt,
        iterations,
    )
    return compare_digest(actual, expected)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
