from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.application.subscriptions.entitlements import EntitlementService
from app.domain.subscriptions.entitlement import EntitlementGrant
from app.infrastructure.persistence.sqlite_entitlement_store import SQLiteEntitlementStore


NOW = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)


def make_grant(**changes) -> EntitlementGrant:
    values = {
        "grant_id": uuid4(),
        "user_id": uuid4(),
        "capability": "technical-indicator-history",
        "starts_at": NOW,
        "expires_at": NOW + timedelta(days=30),
        "granted_by": uuid4(),
        "reason": "verified test grant",
        "created_at": NOW,
    }
    values.update(changes)
    return EntitlementGrant(**values)


def test_entitlement_grant_is_idempotent_and_persists(tmp_path) -> None:
    store = SQLiteEntitlementStore(tmp_path / "entitlements.db")
    grant = make_grant()
    assert store.grant(grant) == grant
    assert store.grant(grant) == grant
    reopened = SQLiteEntitlementStore(tmp_path / "entitlements.db")
    assert reopened.get(grant.grant_id) == grant
    assert reopened.for_user(grant.user_id) == (grant,)


def test_entitlement_service_enforces_time_and_revocation(tmp_path) -> None:
    store = SQLiteEntitlementStore(tmp_path / "entitlements.db")
    grant = make_grant()
    store.grant(grant)
    service = EntitlementService(store)

    assert not service.allows(grant.user_id, grant.capability, at=NOW - timedelta(seconds=1))
    assert service.allows(grant.user_id, grant.capability, at=NOW)
    assert not service.allows(grant.user_id, grant.capability, at=grant.expires_at)

    store.revoke(
        grant.grant_id,
        revoked_at=NOW + timedelta(hours=1),
        revoked_by=grant.granted_by,
        reason="test revocation",
    )
    assert not service.allows(grant.user_id, grant.capability, at=NOW + timedelta(hours=2))


def test_revoke_replay_is_idempotent_but_conflicting_revoke_is_rejected(tmp_path) -> None:
    store = SQLiteEntitlementStore(tmp_path / "entitlements.db")
    grant = make_grant()
    store.grant(grant)
    revoked = store.revoke(
        grant.grant_id,
        revoked_at=NOW + timedelta(hours=1),
        revoked_by=grant.granted_by,
        reason="test revocation",
    )
    assert revoked is not None
    assert store.revoke(
        grant.grant_id,
        revoked_at=NOW + timedelta(hours=2),
        revoked_by=grant.granted_by,
        reason="test revocation",
    ) == revoked
    with pytest.raises(ValueError, match="already revoked differently"):
        store.revoke(
            grant.grant_id,
            revoked_at=NOW + timedelta(hours=2),
            revoked_by=uuid4(),
            reason="different reason",
        )


def test_grant_rejects_naive_dates_and_invalid_expiry() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        make_grant(starts_at=datetime(2026, 10, 26, 12))
    with pytest.raises(ValueError, match="later than starts_at"):
        make_grant(expires_at=NOW)
