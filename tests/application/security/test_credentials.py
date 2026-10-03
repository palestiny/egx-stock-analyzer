from datetime import datetime, timezone
from uuid import UUID

from app.application.security.credentials import (
    CredentialService,
    StoredCredential,
    verify_secret,
)


class InMemoryCredentialStore:
    def __init__(self) -> None:
        self.items: dict[UUID, tuple[StoredCredential, str]] = {}

    def create(self, credential: StoredCredential, verifier: str) -> None:
        self.items[credential.id] = (credential, verifier)

    def find_active_credential(self, secret: str):
        for credential, verifier in self.items.values():
            if credential.status == "active" and verify_secret(secret, verifier):
                return credential
        return None

    def find_active_user_id(self, secret: str):
        credential = self.find_active_credential(secret)
        return credential.user_id if credential else None

    def find_active_for_user(self, user_id: UUID) -> list[StoredCredential]:
        return [
            credential
            for credential, _ in self.items.values()
            if credential.user_id == user_id and credential.status == "active"
        ]

    def replace(
        self,
        credential_id: UUID,
        user_id: UUID,
        replacement: StoredCredential,
        replacement_verifier: str,
        revoked_at: datetime,
    ) -> None:
        current, verifier = self.items[credential_id]
        assert current.user_id == user_id
        self.items[credential_id] = (
            StoredCredential(
                id=current.id,
                user_id=current.user_id,
                status="revoked",
                created_at=current.created_at,
                revoked_at=revoked_at,
                replaced_by=replacement.id,
            ),
            verifier,
        )
        self.items[replacement.id] = (replacement, replacement_verifier)

    def revoke(self, credential_id: UUID, revoked_at: datetime, replacement_id=None) -> None:
        current, verifier = self.items[credential_id]
        self.items[credential_id] = (
            StoredCredential(
                id=current.id,
                user_id=current.user_id,
                status="revoked",
                created_at=current.created_at,
                revoked_at=revoked_at,
                replaced_by=replacement_id,
            ),
            verifier,
        )


def test_provision_returns_secret_but_store_keeps_only_verifier() -> None:
    store = InMemoryCredentialStore()
    service = CredentialService(store)
    user_id = UUID("10000000-0000-0000-0000-000000000001")

    issued = service.provision(user_id)

    stored, verifier = store.items[issued.id]
    assert issued.secret
    assert issued.secret not in verifier
    assert verify_secret(issued.secret, verifier)
    assert stored.user_id == user_id
    assert stored.status == "active"


def test_rotation_revokes_old_credential_and_invalidates_old_secret() -> None:
    store = InMemoryCredentialStore()
    service = CredentialService(store)
    user_id = UUID("10000000-0000-0000-0000-000000000002")

    original = service.provision(user_id)
    replacement = service.rotate(original.id, user_id)

    old = store.items[original.id][0]
    assert old.status == "revoked"
    assert old.replaced_by == replacement.id
    assert store.find_active_user_id(original.secret) is None
    assert store.find_active_user_id(replacement.secret) == user_id


def test_verifier_rejects_wrong_secret() -> None:
    store = InMemoryCredentialStore()
    service = CredentialService(store)
    user_id = UUID("10000000-0000-0000-0000-000000000003")

    issued = service.provision(user_id)
    _, verifier = store.items[issued.id]

    assert not verify_secret("not-the-issued-secret", verifier)


def test_credential_secrets_are_not_recoverable_from_stored_credentials() -> None:
    store = InMemoryCredentialStore()
    service = CredentialService(store)
    issued = service.provision(UUID("10000000-0000-0000-0000-000000000004"))

    stored, _ = store.items[issued.id]
    assert not hasattr(stored, "secret")
    assert issued.secret != stored.id.hex
