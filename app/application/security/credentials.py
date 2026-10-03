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


@dataclass(frozen=True)
class PreparedCredential:
    issued: IssuedCredential
    stored: StoredCredential
    verifier: str


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

    def prepare_provision(self, user_id: UUID) -> PreparedCredential:
        credential_id = uuid4()
        secret = token_urlsafe(32)
        stored = StoredCredential(
            id=credential_id,
            user_id=user_id,
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        return PreparedCredential(
            issued=IssuedCredential(id=credential_id, user_id=user_id, secret=secret),
            stored=stored,
            verifier=_derive_verifier(secret),
        )

    def provision(self, user_id: UUID) -> IssuedCredential:
        prepared = self.prepare_provision(user_id)
        self._store.create(prepared.stored, prepared.verifier)
        return prepared.issued

    def prepare_rotation(self, credential_id: UUID, user_id: UUID) -> tuple[PreparedCredential, datetime]:
        replacement_id = uuid4()
        secret = token_urlsafe(32)
        replacement = StoredCredential(
            id=replacement_id,
            user_id=user_id,
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        return (
            PreparedCredential(
                issued=IssuedCredential(id=replacement_id, user_id=user_id, secret=secret),
                stored=replacement,
                verifier=_derive_verifier(secret),
            ),
            datetime.now(timezone.utc),
        )

    def rotate(self, credential_id: UUID, user_id: UUID) -> IssuedCredential:
        prepared, revoked_at = self.prepare_rotation(credential_id, user_id)
        self._store.replace(
            credential_id=credential_id,
            user_id=user_id,
            replacement=prepared.stored,
            replacement_verifier=prepared.verifier,
            revoked_at=revoked_at,
        )
        return prepared.issued

    def active_credentials_for_user(self, user_id: UUID) -> list[StoredCredential]:
        return self._store.find_active_for_user(user_id)

    def rotate_latest_for_user(self, user_id: UUID) -> IssuedCredential:
        active = self.active_credentials_for_user(user_id)
        if not active:
            raise ValueError("No durable credential is available for this user")
        return self.rotate(active[-1].id, user_id)

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
