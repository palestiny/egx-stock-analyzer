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

    def find_active_for_user(self, user_id: UUID) -> list[StoredCredential]:
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

    def rotate_latest_for_user(self, user_id: UUID) -> IssuedCredential:
        active = self._store.find_active_for_user(user_id)
        if not active:
            raise ValueError("No durable credential is available for this user")
        return self.rotate(active[-1].id, user_id)

    def revoke(self, credential_id: UUID) -> None:
        self._store.revoke(
            credential_id,
            revoked_at=datetime.now(timezone.utc),
        )


def credential_lookup_key(secret: str) -> str:
    """Return a fast indexed verifier for high-entropy opaque bearer tokens."""
    import hashlib

    return "sha256$" + hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _derive_verifier(secret: str) -> str:
    return credential_lookup_key(secret)


def verify_secret(secret: str, verifier: str) -> bool:
    import base64
    import hashlib
    from secrets import compare_digest

    try:
        algorithm, *parts = verifier.split("$")
        if algorithm == "sha256" and len(parts) == 1:
            actual = hashlib.sha256(secret.encode("utf-8")).hexdigest()
            return compare_digest(actual, parts[0])
        if algorithm != "pbkdf2_sha256" or len(parts) != 3:
            return False
        raw_iterations, raw_salt, raw_digest = parts
        iterations = int(raw_iterations)
        if not 1 <= iterations <= 2_000_000:
            return False
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
