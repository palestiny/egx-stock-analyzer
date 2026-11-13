from datetime import date, datetime, timezone
from hashlib import sha256
from uuid import UUID

import pytest

from app.application.market_data.calendar_source_authenticity import (
    CalendarSourceAuthenticityError,
    CalendarSourceAuthenticityVerifier,
    RetrievedCalendarSourceArtifact,
    TrustedCalendarSourceOrigin,
)
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.domain.market_data.calendar_evidence import (
    CalendarArtifactRetention,
    CalendarEvidence,
    CalendarEvidenceKind,
    CalendarEvidenceSourceClass,
)


NOW = datetime(2026, 11, 13, 10, tzinfo=timezone.utc)
UPLOADER_ID = UUID("10000000-0000-0000-0000-000000000001")
UPLOADER_CREDENTIAL = UUID("20000000-0000-0000-0000-000000000001")
REVIEWER_ID = UUID("10000000-0000-0000-0000-000000000002")
REVIEWER_CREDENTIAL = UUID("20000000-0000-0000-0000-000000000002")
CONTENT = b"EGX official schedule notice - immutable test bytes"
DIGEST = sha256(CONTENT).hexdigest()
URL = "https://calendar.example.test/notices/2026-11-13"


def _identity(user_id, credential_id):
    return AuthenticatedIdentity.user(
        user_id,
        credential_id=credential_id,
        permissions=frozenset({Permission.OPERATOR}),
    )


def _evidence(**overrides):
    values = dict(
        calendar_version="calendar-v1",
        session_date=date(2026, 11, 13),
        evidence_kind=CalendarEvidenceKind.SCHEDULE,
        source_type="OFFICIAL_NOTICE",
        source_reference=URL,
        claim="The notice confirms the scheduled EGX session for 2026-11-13",
        recorded_by=UPLOADER_ID,
        recorded_by_credential_id=UPLOADER_CREDENTIAL,
        observed_at=NOW,
        recorded_at=NOW,
        source_class=CalendarEvidenceSourceClass.A,
        source_publisher="EGX",
        market_scope="EGX_MARKET_WIDE",
        effective_from=date(2026, 11, 13),
        effective_through=date(2026, 11, 13),
        retrieved_at=NOW,
        artifact_sha256=DIGEST,
        artifact_retention=CalendarArtifactRetention.EXTERNAL_ONLY,
        artifact_not_retained_reason="Retention permission has not been established",
    )
    values.update(overrides)
    return CalendarEvidence.create(**values)


class _Origins:
    def __init__(self, trust=None):
        self.trust = trust

    def get_exact_origin(self, origin, *, at):
        if self.trust is not None and self.trust.origin == origin:
            return self.trust
        return None


class _Records:
    def __init__(self):
        self.items = []

    def append(self, record):
        self.items.append(record)

    def latest(self, evidence_id):
        matches = [item for item in self.items if item.evidence_id == evidence_id]
        return matches[-1] if matches else None


class _Retriever:
    def __init__(self, result=None):
        self.result = result or RetrievedCalendarSourceArtifact(
            requested_url=URL,
            final_url=URL,
            redirect_urls=(),
            tls_verified=True,
            status_code=200,
            content=CONTENT,
            content_type="application/pdf",
        )
        self.calls = []

    def retrieve(self, url):
        self.calls.append(url)
        return self.result


def _trust(**overrides):
    values = dict(
        origin="https://calendar.example.test",
        publisher="EGX",
        source_class="A",
        market_scope="EGX_MARKET_WIDE",
        trust_basis="Owner-approved exact origin record; test fixture only",
        registry_version="origin-registry-v1",
        approved_by=UUID("30000000-0000-0000-0000-000000000001"),
        approved_by_credential_id=UUID("40000000-0000-0000-0000-000000000001"),
        approved_at=NOW,
    )
    values.update(overrides)
    return TrustedCalendarSourceOrigin(**values)


_DEFAULT_TRUST = object()


def _verifier(retriever=None, trust=_DEFAULT_TRUST, records=None):
    records = records or _Records()
    trust_record = _trust() if trust is _DEFAULT_TRUST else trust
    verifier = CalendarSourceAuthenticityVerifier(
        origins=_Origins(trust_record),
        records=records,
        retriever=retriever or _Retriever(),
    )
    return verifier, records


def test_verification_requires_exact_approved_origin_and_independent_review():
    verifier, records = _verifier()
    result = verifier.verify_for_activation(
        _evidence(),
        uploader=_identity(UPLOADER_ID, UPLOADER_CREDENTIAL),
        verifier=_identity(REVIEWER_ID, REVIEWER_CREDENTIAL),
        reviewed_claim=_evidence().claim,
        claim_supported=True,
        at=NOW,
    )
    assert result.decision.value == "VERIFIED"
    assert result.uploader_user_id == UPLOADER_ID
    assert result.verifier_user_id == REVIEWER_ID
    assert result.artifact_sha256 == DIGEST
    assert records.latest(result.evidence_id) == result


def test_unapproved_origin_fails_even_when_publisher_metadata_says_egx():
    verifier, records = _verifier(trust=None)
    with pytest.raises(CalendarSourceAuthenticityError, match="not explicitly owner-approved"):
        verifier.verify_for_activation(
            _evidence(),
            uploader=_identity(UPLOADER_ID, UPLOADER_CREDENTIAL),
            verifier=_identity(REVIEWER_ID, REVIEWER_CREDENTIAL),
            reviewed_claim=_evidence().claim,
            claim_supported=True,
            at=NOW,
        )
    assert records.items == []


@pytest.mark.parametrize("url", [
    "http://calendar.example.test/notice",
    "https://calendar.example.test.evil.test/notice",
    "https://calendar.example.test:444/notice",
    "https://user@calendar.example.test/notice",
])
def test_unsafe_or_lookalike_source_urls_are_rejected(url):
    from app.application.market_data.calendar_source_authenticity import normalize_calendar_source_origin
    with pytest.raises(CalendarSourceAuthenticityError):
        normalize_calendar_source_origin(url)


def test_cross_origin_redirect_is_rejected():
    retrieved = RetrievedCalendarSourceArtifact(
        requested_url=URL,
        final_url="https://mirror.example.test/notice",
        redirect_urls=("https://mirror.example.test/notice",),
        tls_verified=True,
        status_code=200,
        content=CONTENT,
    )
    verifier, _ = _verifier(retriever=_Retriever(retrieved))
    with pytest.raises(CalendarSourceAuthenticityError, match="Redirects are not accepted"):
        verifier.verify_for_activation(
            _evidence(),
            uploader=_identity(UPLOADER_ID, UPLOADER_CREDENTIAL),
            verifier=_identity(REVIEWER_ID, REVIEWER_CREDENTIAL),
            reviewed_claim=_evidence().claim,
            claim_supported=True,
            at=NOW,
        )


def test_invalid_tls_and_changed_artifact_fail_closed():
    bad_tls = RetrievedCalendarSourceArtifact(URL, URL, (), False, 200, CONTENT)
    verifier, _ = _verifier(retriever=_Retriever(bad_tls))
    with pytest.raises(CalendarSourceAuthenticityError, match="TLS"):
        verifier.verify_for_activation(
            _evidence(),
            uploader=_identity(UPLOADER_ID, UPLOADER_CREDENTIAL),
            verifier=_identity(REVIEWER_ID, REVIEWER_CREDENTIAL),
            reviewed_claim=_evidence().claim,
            claim_supported=True,
            at=NOW,
        )

    changed = RetrievedCalendarSourceArtifact(URL, URL, (), True, 200, b"changed")
    verifier, _ = _verifier(retriever=_Retriever(changed))
    with pytest.raises(CalendarSourceAuthenticityError, match="does not match"):
        verifier.verify_for_activation(
            _evidence(),
            uploader=_identity(UPLOADER_ID, UPLOADER_CREDENTIAL),
            verifier=_identity(REVIEWER_ID, REVIEWER_CREDENTIAL),
            reviewed_claim=_evidence().claim,
            claim_supported=True,
            at=NOW,
        )


def test_uploader_cannot_self_verify_and_claim_review_must_be_exact():
    verifier, _ = _verifier()
    with pytest.raises(CalendarSourceAuthenticityError, match="different people"):
        verifier.verify_for_activation(
            _evidence(),
            uploader=_identity(UPLOADER_ID, UPLOADER_CREDENTIAL),
            verifier=_identity(UPLOADER_ID, UUID("20000000-0000-0000-0000-000000000003")),
            reviewed_claim=_evidence().claim,
            claim_supported=True,
            at=NOW,
        )
    with pytest.raises(CalendarSourceAuthenticityError, match="exact evidence claim"):
        verifier.verify_for_activation(
            _evidence(),
            uploader=_identity(UPLOADER_ID, UPLOADER_CREDENTIAL),
            verifier=_identity(REVIEWER_ID, REVIEWER_CREDENTIAL),
            reviewed_claim="A different claim",
            claim_supported=True,
            at=NOW,
        )


def test_external_only_artifact_is_refetched_at_each_activation_decision():
    retriever = _Retriever()
    verifier, records = _verifier(retriever=retriever)
    evidence = _evidence()
    verifier.verify_for_activation(
        evidence,
        uploader=_identity(UPLOADER_ID, UPLOADER_CREDENTIAL),
        verifier=_identity(REVIEWER_ID, REVIEWER_CREDENTIAL),
        reviewed_claim=evidence.claim,
        claim_supported=True,
        at=NOW,
    )
    verifier.revalidate_for_activation(evidence, at=NOW)
    assert retriever.calls == [URL, URL]

    retriever.result = RetrievedCalendarSourceArtifact(URL, URL, (), True, 200, b"changed")
    with pytest.raises(CalendarSourceAuthenticityError, match="bytes changed"):
        verifier.revalidate_for_activation(evidence, at=NOW)
