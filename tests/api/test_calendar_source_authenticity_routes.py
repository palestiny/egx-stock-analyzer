from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from app.api.calendar_source_authenticity_routes import (
    create_calendar_source_authenticity_router,
)
from app.application.market_data.calendar_source_authenticity import (
    CalendarSourceAuthenticityVerifier,
    RetrievedCalendarSourceArtifact,
)
from app.application.market_data.review_calendar_evidence_authenticity import (
    ReviewCalendarEvidenceAuthenticity,
)
from app.application.security.credentials import CredentialService
from app.application.security.identity import AuthenticatedIdentity, Permission
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
from app.infrastructure.persistence.sqlite_calendar_evidence_uploader_identity_resolver import (
    SQLiteCalendarEvidenceUploaderIdentityResolver,
)
from app.infrastructure.persistence.sqlite_calendar_evidence_verification_store import (
    SQLiteCalendarEvidenceVerificationStore,
)
from app.infrastructure.persistence.sqlite_calendar_source_origin_registry import (
    SQLiteCalendarSourceOriginRegistry,
)
from app.infrastructure.persistence.sqlite_credential_store import SQLiteCredentialStore
from app.infrastructure.persistence.sqlite_operator_access_store import SQLiteOperatorAccessStore
from app.infrastructure.persistence.sqlite_session_calendar_repository import (
    SQLiteSessionCalendarRepository,
)
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore


NOW = datetime(2026, 11, 13, 10, tzinfo=timezone.utc)
CONTENT = b"official EGX calendar notice bytes"
SOURCE_URL = "https://official.example.test/notice"


class FakeRetriever:
    def retrieve(self, url):
        assert url == SOURCE_URL
        return RetrievedCalendarSourceArtifact(
            requested_url=url,
            final_url=url,
            redirect_urls=(),
            tls_verified=True,
            status_code=200,
            content=CONTENT,
            content_type="application/pdf",
        )


def make_client(tmp_path):
    database = tmp_path / "calendar-authenticity-api.db"
    user_store = SQLiteUserStore(database)
    credential_store = SQLiteCredentialStore(database)
    credential_service = CredentialService(credential_store)
    users = [uuid4(), uuid4(), uuid4()]
    credentials = {}
    for user_id in users:
        user_store.save(User(user_id, UserStatus.ACTIVE))
        credentials[user_id] = credential_service.provision(user_id)

    owner_id, uploader_id, reviewer_id = users
    operator_access = SQLiteOperatorAccessStore(database)
    operator_access.bootstrap_first_operator(owner_id, reason="API test owner bootstrap")
    for target_id in (uploader_id, reviewer_id):
        operator_access.grant(
            target_id,
            actor_user_id=owner_id,
            actor_credential_id=credentials[owner_id].id,
            reason="API test individual operator grant",
        )

    calendar = EGXSessionCalendar(
        version="auth-api-v1",
        timezone="Africa/Cairo",
        coverage_start=date(2026, 11, 13),
        coverage_end=date(2026, 11, 13),
        days=(EGXCalendarDay(date(2026, 11, 13), CalendarDayStatus.NON_TRADING),),
    )
    SQLiteSessionCalendarRepository(database).publish(
        calendar,
        published_by="api-test",
        source_reference="fixture",
        reason="fixture",
    )
    evidence = CalendarEvidence.create(
        calendar_version="auth-api-v1",
        session_date=date(2026, 11, 13),
        evidence_kind=CalendarEvidenceKind.CLOSURE,
        source_type="OFFICIAL_NOTICE",
        source_reference=SOURCE_URL,
        claim="The official notice confirms the EGX non-trading date",
        recorded_by=uploader_id,
        recorded_by_credential_id=credentials[uploader_id].id,
        observed_at=NOW,
        recorded_at=NOW,
        source_class=CalendarEvidenceSourceClass.A,
        source_publisher="EGX",
        market_scope="EGX_MARKET_WIDE",
        effective_from=date(2026, 11, 13),
        effective_through=date(2026, 11, 13),
        retrieved_at=NOW,
        artifact_sha256=sha256(CONTENT).hexdigest(),
        artifact_retention=CalendarArtifactRetention.EXTERNAL_ONLY,
        artifact_not_retained_reason="API test does not retain external bytes",
    )
    evidence_repository = SQLiteCalendarEvidenceRepository(database)
    evidence_repository.append(evidence)

    origin_registry = SQLiteCalendarSourceOriginRegistry(
        database, owner_user_id=owner_id
    )
    verification_store = SQLiteCalendarEvidenceVerificationStore(database)
    verifier = CalendarSourceAuthenticityVerifier(
        origins=origin_registry,
        records=verification_store,
        retriever=FakeRetriever(),
    )
    review_service = ReviewCalendarEvidenceAuthenticity(
        evidence_repository=evidence_repository,
        uploader_identity_resolver=SQLiteCalendarEvidenceUploaderIdentityResolver(database),
        verifier=verifier,
    )

    tokens = {
        "owner-test-token": owner_id,
        "uploader-test-token": uploader_id,
        "reviewer-test-token": reviewer_id,
    }

    def require_individual_operator(
        authorization: str | None = Header(default=None),
    ) -> AuthenticatedIdentity:
        token = authorization.removeprefix("Bearer ") if authorization else ""
        user_id = tokens.get(token)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        return AuthenticatedIdentity.user(
            user_id,
            credential_id=credentials[user_id].id,
            permissions=frozenset({Permission.OPERATOR}),
        )

    app = FastAPI()
    app.include_router(
        create_calendar_source_authenticity_router(
            origin_registry=origin_registry,
            review_service=review_service,
            require_individual_operator=require_individual_operator,
        )
    )
    return (
        TestClient(app),
        evidence,
        origin_registry,
        verification_store,
        owner_id,
        uploader_id,
        reviewer_id,
    )


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_owner_approves_exact_origin_and_separate_reviewer_verifies_evidence(tmp_path):
    client, evidence, _origins, records, _owner, _uploader, _reviewer = make_client(tmp_path)
    approval = client.post(
        "/api/v1/owner/session-calendar-source-origins",
        headers=_headers("owner-test-token"),
        json={
            "origin": "https://official.example.test/",
            "publisher": "EGX",
            "source_class": "A",
            "market_scope": "EGX_MARKET_WIDE",
            "trust_basis": "Owner independently reviewed the exact official origin",
            "registry_version": "owner-origin-v1",
        },
    )
    assert approval.status_code == 201
    assert approval.json()["origin"] == "https://official.example.test"

    reviewed = client.post(
        f"/api/v1/operator/session-calendars/evidence/{evidence.evidence_id}/authenticity-review",
        headers=_headers("reviewer-test-token"),
        json={
            "reviewed_claim": evidence.claim,
            "claim_supported": True,
        },
    )
    assert reviewed.status_code == 201
    assert reviewed.json()["decision"] == "VERIFIED"
    assert records.latest(evidence.evidence_id).verifier_user_id == UUID(
        reviewed.json()["verifier_user_id"]
    )


def test_non_owner_cannot_change_source_origin_trust(tmp_path):
    client, _evidence, _origins, _records, _owner, _uploader, _reviewer = make_client(tmp_path)
    response = client.post(
        "/api/v1/owner/session-calendar-source-origins",
        headers=_headers("reviewer-test-token"),
        json={
            "origin": "https://official.example.test",
            "publisher": "EGX",
            "source_class": "A",
            "market_scope": "EGX_MARKET_WIDE",
            "trust_basis": "Not owner-approved",
            "registry_version": "v1",
        },
    )
    assert response.status_code == 403


def test_uploader_cannot_review_own_evidence_and_rejection_is_audited(tmp_path):
    client, evidence, _origins, records, _owner, _uploader, _reviewer = make_client(tmp_path)
    approval = client.post(
        "/api/v1/owner/session-calendar-source-origins",
        headers=_headers("owner-test-token"),
        json={
            "origin": "https://official.example.test",
            "publisher": "EGX",
            "source_class": "A",
            "market_scope": "EGX_MARKET_WIDE",
            "trust_basis": "Owner-reviewed test origin",
            "registry_version": "v1",
        },
    )
    assert approval.status_code == 201

    self_review = client.post(
        f"/api/v1/operator/session-calendars/evidence/{evidence.evidence_id}/authenticity-review",
        headers=_headers("uploader-test-token"),
        json={"reviewed_claim": evidence.claim, "claim_supported": True},
    )
    assert self_review.status_code == 422
    assert "different people" in self_review.json()["detail"]

    rejected = client.post(
        f"/api/v1/operator/session-calendars/evidence/{evidence.evidence_id}/authenticity-review",
        headers=_headers("reviewer-test-token"),
        json={
            "reviewed_claim": evidence.claim,
            "claim_supported": False,
            "review_reason": "The artifact does not support the stated closure claim",
        },
    )
    assert rejected.status_code == 201
    assert rejected.json()["decision"] == "REJECTED"
    assert records.latest(evidence.evidence_id).decision.value == "REJECTED"
