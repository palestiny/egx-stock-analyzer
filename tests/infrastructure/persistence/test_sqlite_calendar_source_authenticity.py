import sqlite3
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.market_data.calendar_source_authenticity import (
    CalendarEvidenceVerificationRecord,
    CalendarSourceVerificationDecision,
)
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.application.security.credentials import CredentialService
from app.domain.identity.user import User, UserStatus
from app.domain.market_data.calendar_evidence import (
    CalendarArtifactRetention,
    CalendarEvidence,
    CalendarEvidenceKind,
    CalendarEvidenceSourceClass,
)
from app.domain.market_data.session_calendar import (
    CalendarDayStatus,
    EGXCalendarDay,
    EGXSessionCalendar,
)
from app.infrastructure.persistence.sqlite_calendar_evidence_repository import (
    SQLiteCalendarEvidenceRepository,
)
from app.infrastructure.persistence.sqlite_calendar_evidence_verification_store import (
    SQLiteCalendarEvidenceVerificationStore,
)
from app.infrastructure.persistence.sqlite_calendar_source_origin_registry import (
    SQLiteCalendarSourceOriginRegistry,
)
from app.infrastructure.persistence.sqlite_credential_store import SQLiteCredentialStore
from app.infrastructure.persistence.sqlite_session_calendar_repository import (
    SQLiteSessionCalendarRepository,
)
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore


NOW = datetime(2026, 11, 13, 10, tzinfo=timezone.utc)


def _database(tmp_path):
    path = tmp_path / "calendar-authenticity.db"
    users = SQLiteUserStore(path)
    credentials = SQLiteCredentialStore(path)
    calendar = EGXSessionCalendar(
        version="auth-v1",
        timezone="Africa/Cairo",
        coverage_start=date(2026, 11, 13),
        coverage_end=date(2026, 11, 13),
        days=(EGXCalendarDay(date(2026, 11, 13), CalendarDayStatus.NON_TRADING),),
    )
    SQLiteSessionCalendarRepository(path).publish(
        calendar, published_by="schema", source_reference="fixture", reason="fixture"
    )
    actor_ids = [uuid4(), uuid4()]
    users.save(User(actor_ids[0], UserStatus.ACTIVE))
    users.save(User(actor_ids[1], UserStatus.ACTIVE))
    service = CredentialService(credentials)
    creds = [service.provision(actor_ids[0]), service.provision(actor_ids[1])]
    evidence = CalendarEvidence.create(
        calendar_version="auth-v1",
        session_date=date(2026, 11, 13),
        evidence_kind=CalendarEvidenceKind.CLOSURE,
        source_type="OFFICIAL_NOTICE",
        source_reference="https://official.example.test/notice",
        claim="EGX closure notice",
        recorded_by=actor_ids[0],
        recorded_by_credential_id=creds[0].id,
        observed_at=NOW,
        recorded_at=NOW,
        source_class=CalendarEvidenceSourceClass.A,
        source_publisher="EGX",
        market_scope="EGX_MARKET_WIDE",
        effective_from=date(2026, 11, 13),
        effective_through=date(2026, 11, 13),
        retrieved_at=NOW,
        artifact_sha256="a" * 64,
        artifact_retention=CalendarArtifactRetention.EXTERNAL_ONLY,
        artifact_not_retained_reason="Test fixture",
    )
    stored_evidence = SQLiteCalendarEvidenceRepository(path).append(evidence)
    return path, actor_ids, creds, stored_evidence


def test_origin_registry_requires_configured_owner_and_active_durable_credential(tmp_path):
    path, actor_ids, creds, _ = _database(tmp_path)
    registry = SQLiteCalendarSourceOriginRegistry(path, owner_user_id=actor_ids[0])
    non_owner = AuthenticatedIdentity.user(
        actor_ids[1], credential_id=creds[1].id,
        permissions=frozenset({Permission.OPERATOR}),
    )
    with pytest.raises(PermissionError, match="configured owner"):
        registry.approve_origin(
            "https://official.example.test",
            publisher="EGX",
            source_class="A",
            market_scope="EGX_MARKET_WIDE",
            trust_basis="Explicit owner review of exact origin",
            registry_version="v1",
            owner=non_owner,
            occurred_at=NOW,
        )


def test_origin_approval_is_exact_owner_attributed_and_revocable(tmp_path):
    path, actor_ids, creds, _ = _database(tmp_path)
    registry = SQLiteCalendarSourceOriginRegistry(path, owner_user_id=actor_ids[0])
    owner = AuthenticatedIdentity.user(
        actor_ids[0], credential_id=creds[0].id,
        permissions=frozenset({Permission.OPERATOR}),
    )
    approved = registry.approve_origin(
        "https://official.example.test/",
        publisher="EGX",
        source_class="A",
        market_scope="EGX_MARKET_WIDE",
        trust_basis="Explicit owner review of the exact HTTPS origin",
        registry_version="v1",
        owner=owner,
        occurred_at=NOW,
    )
    assert approved.origin == "https://official.example.test"
    assert registry.get_exact_origin(approved.origin, at=NOW) == approved
    assert registry.get_exact_origin("https://sub.official.example.test", at=NOW) is None

    registry.revoke_origin(
        approved.origin,
        reason="Trust basis no longer valid",
        registry_version="v2",
        owner=owner,
        occurred_at=datetime(2026, 11, 14, tzinfo=timezone.utc),
    )
    assert registry.get_exact_origin(
        approved.origin, at=datetime(2026, 11, 14, tzinfo=timezone.utc)
    ) is None
    assert [item["action"] for item in registry.list_events()] == ["APPROVE", "REVOKE"]


def test_verification_records_are_append_only_and_latest_is_durable(tmp_path):
    path, actor_ids, creds, evidence = _database(tmp_path)
    store = SQLiteCalendarEvidenceVerificationStore(path)
    record = CalendarEvidenceVerificationRecord(
        evidence_id=evidence.evidence_id,
        decision=CalendarSourceVerificationDecision.VERIFIED,
        source_origin="https://official.example.test",
        registry_version="origin-v1",
        artifact_sha256="a" * 64,
        verifier_user_id=actor_ids[1],
        verifier_credential_id=creds[1].id,
        uploader_user_id=actor_ids[0],
        uploader_credential_id=creds[0].id,
        reviewed_claim_sha256="b" * 64,
        method_version="origin-and-independent-review-v1",
        verified_at=NOW,
        reason="Independent review confirmed the exact claim",
    )
    store.append(record)
    recreated = SQLiteCalendarEvidenceVerificationStore(path)
    assert recreated.latest(evidence.evidence_id) == record

    with recreated._connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE egx_calendar_evidence_verifications SET reason = 'rewritten'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("DELETE FROM egx_calendar_evidence_verifications")
