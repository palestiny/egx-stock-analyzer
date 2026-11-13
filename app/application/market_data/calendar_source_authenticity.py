from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import ipaddress
from typing import Protocol
from urllib.parse import urlsplit
from uuid import UUID

from app.application.security.identity import AuthenticatedIdentity, Permission
from app.application.market_data.calendar_artifact_storage import (
    CalendarArtifactService,
)
from app.domain.market_data.calendar_evidence import (
    CalendarArtifactRetention,
    CalendarEvidence,
)


class CalendarSourceAuthenticityError(ValueError):
    """A calendar evidence item cannot be independently authenticated."""


class CalendarSourceVerificationDecision(StrEnum):
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class TrustedCalendarSourceOrigin:
    """One exact HTTPS origin explicitly approved by the product owner."""

    origin: str
    publisher: str
    source_class: str
    market_scope: str
    trust_basis: str
    registry_version: str
    approved_by: UUID
    approved_by_credential_id: UUID
    approved_at: datetime
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        normalized = normalize_calendar_source_origin(self.origin)
        if normalized != self.origin:
            raise ValueError("Trusted origin must be stored in canonical exact-origin form")
        for field_name in (
            "publisher", "source_class", "market_scope", "trust_basis",
            "registry_version",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be non-empty")
        _require_aware(self.approved_at, "approved_at")
        if self.revoked_at is not None:
            _require_aware(self.revoked_at, "revoked_at")
            if self.revoked_at < self.approved_at:
                raise ValueError("revoked_at cannot precede approved_at")

    def is_active_at(self, at: datetime) -> bool:
        _require_aware(at, "verification timestamp")
        return self.approved_at <= at and (
            self.revoked_at is None or at < self.revoked_at
        )


@dataclass(frozen=True)
class RetrievedCalendarSourceArtifact:
    requested_url: str
    final_url: str
    redirect_urls: tuple[str, ...]
    tls_verified: bool
    status_code: int
    content: bytes
    content_type: str | None = None


class CalendarSourceArtifactRetriever(Protocol):
    """Transport must validate TLS and must not follow redirects implicitly."""

    def retrieve(self, url: str) -> RetrievedCalendarSourceArtifact: ...


class CalendarSourceOriginRegistry(Protocol):
    def get_exact_origin(self, origin: str, *, at: datetime) -> TrustedCalendarSourceOrigin | None: ...


class CalendarEvidenceVerificationStore(Protocol):
    def append(self, record: "CalendarEvidenceVerificationRecord") -> None: ...

    def latest(self, evidence_id: UUID) -> "CalendarEvidenceVerificationRecord | None": ...


@dataclass(frozen=True)
class CalendarEvidenceVerificationRecord:
    evidence_id: UUID
    decision: CalendarSourceVerificationDecision
    source_origin: str
    registry_version: str
    artifact_sha256: str
    verifier_user_id: UUID
    verifier_credential_id: UUID
    uploader_user_id: UUID
    uploader_credential_id: UUID
    reviewed_claim_sha256: str
    method_version: str
    verified_at: datetime
    reason: str

    def __post_init__(self) -> None:
        _require_aware(self.verified_at, "verified_at")
        if len(self.artifact_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.artifact_sha256
        ):
            raise ValueError("artifact_sha256 must be a lowercase SHA-256 digest")
        if len(self.reviewed_claim_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.reviewed_claim_sha256
        ):
            raise ValueError("reviewed_claim_sha256 must be a lowercase SHA-256 digest")
        if not self.reason.strip() or not self.method_version.strip():
            raise ValueError("Verification reason and method version are required")


def normalize_calendar_source_origin(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise CalendarSourceAuthenticityError("Source reference must be a non-empty URL")
    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() != "https":
        raise CalendarSourceAuthenticityError("Calendar source must use HTTPS")
    if not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise CalendarSourceAuthenticityError("Calendar source URL has an invalid authority")
    if parsed.fragment:
        raise CalendarSourceAuthenticityError("Calendar source URL must not contain a fragment")
    if parsed.hostname.endswith("."):
        raise CalendarSourceAuthenticityError("Trailing-dot source hostnames are not accepted")
    try:
        ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        raise CalendarSourceAuthenticityError("Calendar source origins must use an approved DNS hostname, not an IP literal")
    try:
        port = parsed.port
    except ValueError as error:
        raise CalendarSourceAuthenticityError("Calendar source URL has an invalid port") from error
    if port not in (None, 443):
        raise CalendarSourceAuthenticityError("Only the standard HTTPS origin is permitted")
    hostname = parsed.hostname.encode("idna").decode("ascii").lower()
    return f"https://{hostname}"


def _require_aware(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _require_individual_operator(identity: AuthenticatedIdentity, label: str) -> None:
    if (
        Permission.OPERATOR not in identity.permissions
        or identity.user_id is None
        or identity.credential_id is None
        or identity.subject != str(identity.user_id)
    ):
        raise CalendarSourceAuthenticityError(
            f"{label} must be an individually authenticated operator with a durable credential"
        )


def _claim_digest(evidence: CalendarEvidence) -> str:
    material = "\n".join((
        str(evidence.evidence_id),
        evidence.calendar_version,
        evidence.session_date.isoformat(),
        evidence.evidence_kind.value,
        evidence.source_publisher or "",
        evidence.market_scope or "",
        evidence.effective_from.isoformat() if evidence.effective_from else "",
        evidence.effective_through.isoformat() if evidence.effective_through else "",
        evidence.claim,
        evidence.artifact_sha256 or "",
    ))
    return sha256(material.encode("utf-8")).hexdigest()


class CalendarSourceAuthenticityVerifier:
    """Fail-closed Option-B verifier used by the activation preflight gate."""

    METHOD_VERSION = "origin-and-independent-review-v1"

    def __init__(
        self,
        *,
        origins: CalendarSourceOriginRegistry,
        records: CalendarEvidenceVerificationStore,
        retriever: CalendarSourceArtifactRetriever,
        artifact_service: CalendarArtifactService | None = None,
    ) -> None:
        self._origins = origins
        self._records = records
        self._retriever = retriever
        self._artifact_service = artifact_service

    def verify_for_activation(
        self,
        evidence: CalendarEvidence,
        *,
        uploader: AuthenticatedIdentity,
        verifier: AuthenticatedIdentity,
        reviewed_claim: str,
        claim_supported: bool,
        at: datetime | None = None,
    ) -> CalendarEvidenceVerificationRecord:
        timestamp = at or datetime.now(timezone.utc)
        _require_aware(timestamp, "verification timestamp")
        _require_individual_operator(uploader, "Uploader")
        _require_individual_operator(verifier, "Verifier")
        if (
            uploader.user_id != evidence.recorded_by
            or evidence.recorded_by_credential_id is None
            or uploader.credential_id != evidence.recorded_by_credential_id
        ):
            raise CalendarSourceAuthenticityError(
                "Uploader identity and durable credential do not match the immutable evidence actor"
            )
        if (
            verifier.user_id == uploader.user_id
            or verifier.credential_id == uploader.credential_id
        ):
            raise CalendarSourceAuthenticityError(
                "Evidence uploader and independent verifier must be different people and credentials"
            )
        if reviewed_claim != evidence.claim or not claim_supported:
            raise CalendarSourceAuthenticityError(
                "Independent reviewer did not confirm the exact evidence claim"
            )
        if evidence.artifact_sha256 is None or evidence.source_publisher is None:
            raise CalendarSourceAuthenticityError("Evidence lacks required source and artifact metadata")

        origin = normalize_calendar_source_origin(evidence.source_reference)
        trust = self._origins.get_exact_origin(origin, at=timestamp)
        if trust is None or not trust.is_active_at(timestamp):
            raise CalendarSourceAuthenticityError("Source origin is not explicitly owner-approved and active")
        if (
            trust.publisher != evidence.source_publisher
            or trust.source_class != (evidence.source_class.value if evidence.source_class else None)
            or trust.market_scope != evidence.market_scope
        ):
            raise CalendarSourceAuthenticityError(
                "Trusted origin publisher, source class, or market scope does not match evidence"
            )

        retrieved = self._retriever.retrieve(evidence.source_reference)
        self._validate_retrieval(retrieved, evidence.source_reference, origin)
        fetched_digest = sha256(retrieved.content).hexdigest()
        if fetched_digest != evidence.artifact_sha256:
            raise CalendarSourceAuthenticityError(
                "Retrieved source artifact does not match the recorded SHA-256 digest"
            )

        if evidence.artifact_retention is CalendarArtifactRetention.ARCHIVED:
            if self._artifact_service is None or not evidence.artifact_storage_reference:
                raise CalendarSourceAuthenticityError(
                    "Archived evidence cannot be verified without configured byte storage"
                )
            stored_bytes = self._artifact_service.read_verified(
                evidence.artifact_storage_reference, evidence.artifact_sha256
            )
            if sha256(stored_bytes).hexdigest() != fetched_digest:
                raise CalendarSourceAuthenticityError(
                    "Archived bytes differ from the bytes retrieved from the approved source origin"
                )
        elif evidence.artifact_retention is not CalendarArtifactRetention.EXTERNAL_ONLY:
            raise CalendarSourceAuthenticityError("Unsupported artifact retention mode")

        record = CalendarEvidenceVerificationRecord(
            evidence_id=evidence.evidence_id,
            decision=CalendarSourceVerificationDecision.VERIFIED,
            source_origin=origin,
            registry_version=trust.registry_version,
            artifact_sha256=fetched_digest,
            verifier_user_id=verifier.user_id,
            verifier_credential_id=verifier.credential_id,
            uploader_user_id=uploader.user_id,
            uploader_credential_id=uploader.credential_id,
            reviewed_claim_sha256=_claim_digest(evidence),
            method_version=self.METHOD_VERSION,
            verified_at=timestamp,
            reason="Independent reviewer confirmed the exact claim against bytes retrieved from the owner-approved origin",
        )
        self._records.append(record)
        return record

    def revalidate_for_activation(
        self,
        evidence: CalendarEvidence,
        *,
        at: datetime | None = None,
    ) -> CalendarEvidenceVerificationRecord:
        """Preflight the source immediately before an activation transaction."""
        timestamp = at or datetime.now(timezone.utc)
        _require_aware(timestamp, "activation verification timestamp")
        prior = self._records.latest(evidence.evidence_id)
        if (
            prior is None
            or prior.decision is not CalendarSourceVerificationDecision.VERIFIED
            or prior.artifact_sha256 != evidence.artifact_sha256
            or prior.reviewed_claim_sha256 != _claim_digest(evidence)
            or prior.method_version != self.METHOD_VERSION
        ):
            raise CalendarSourceAuthenticityError("No matching independent verification record exists")
        trust = self._origins.get_exact_origin(prior.source_origin, at=timestamp)
        self._assert_trust_matches(trust, evidence, prior, timestamp)

        if evidence.artifact_retention is CalendarArtifactRetention.EXTERNAL_ONLY:
            retrieved = self._retriever.retrieve(evidence.source_reference)
            self._validate_retrieval(retrieved, evidence.source_reference, prior.source_origin)
            actual = sha256(retrieved.content).hexdigest()
            if actual != evidence.artifact_sha256:
                raise CalendarSourceAuthenticityError(
                    "EXTERNAL_ONLY source is unavailable or its bytes changed since independent review"
                )
        elif evidence.artifact_retention is CalendarArtifactRetention.ARCHIVED:
            if self._artifact_service is None or not evidence.artifact_storage_reference:
                raise CalendarSourceAuthenticityError("Archived evidence storage is unavailable")
            self._artifact_service.read_verified(
                evidence.artifact_storage_reference, evidence.artifact_sha256 or ""
            )
        else:
            raise CalendarSourceAuthenticityError("Unsupported artifact retention mode")

        refreshed = CalendarEvidenceVerificationRecord(
            evidence_id=prior.evidence_id,
            decision=prior.decision,
            source_origin=prior.source_origin,
            registry_version=prior.registry_version,
            artifact_sha256=prior.artifact_sha256,
            verifier_user_id=prior.verifier_user_id,
            verifier_credential_id=prior.verifier_credential_id,
            uploader_user_id=prior.uploader_user_id,
            uploader_credential_id=prior.uploader_credential_id,
            reviewed_claim_sha256=prior.reviewed_claim_sha256,
            method_version=prior.method_version,
            verified_at=timestamp,
            reason=(
                "Activation preflight revalidated the approved origin and exact artifact bytes; "
                "the independent claim review remains bound to the same immutable evidence"
            ),
        )
        self._records.append(refreshed)
        return refreshed

    def assert_preflight_verification(
        self,
        evidence: CalendarEvidence,
        *,
        at: datetime,
    ) -> CalendarEvidenceVerificationRecord:
        """Check the preflight record inside the DB transaction without network I/O."""
        _require_aware(at, "activation verification timestamp")
        record = self._records.latest(evidence.evidence_id)
        if (
            record is None
            or record.decision is not CalendarSourceVerificationDecision.VERIFIED
            or record.verified_at != at
            or record.artifact_sha256 != evidence.artifact_sha256
            or record.reviewed_claim_sha256 != _claim_digest(evidence)
            or record.method_version != self.METHOD_VERSION
        ):
            raise CalendarSourceAuthenticityError(
                "A matching source-authenticity preflight record for this activation decision is required"
            )
        trust = self._origins.get_exact_origin(record.source_origin, at=at)
        self._assert_trust_matches(trust, evidence, record, at)
        if evidence.artifact_retention is CalendarArtifactRetention.ARCHIVED:
            if self._artifact_service is None or not evidence.artifact_storage_reference:
                raise CalendarSourceAuthenticityError("Archived evidence storage is unavailable")
            self._artifact_service.read_verified(
                evidence.artifact_storage_reference, evidence.artifact_sha256 or ""
            )
        elif evidence.artifact_retention is not CalendarArtifactRetention.EXTERNAL_ONLY:
            raise CalendarSourceAuthenticityError("Unsupported artifact retention mode")
        return record

    @staticmethod
    def _assert_trust_matches(trust, evidence, record, at: datetime) -> None:
        if (
            trust is None
            or not trust.is_active_at(at)
            or trust.registry_version != record.registry_version
            or trust.publisher != evidence.source_publisher
            or trust.source_class != (evidence.source_class.value if evidence.source_class else None)
            or trust.market_scope != evidence.market_scope
        ):
            raise CalendarSourceAuthenticityError(
                "The source origin trust approval is missing, revoked, or inconsistent with evidence"
            )

    @staticmethod
    def _validate_retrieval(
        retrieved: RetrievedCalendarSourceArtifact,
        requested_url: str,
        expected_origin: str,
    ) -> None:
        if retrieved.requested_url != requested_url:
            raise CalendarSourceAuthenticityError("Retriever response does not match the requested URL")
        if not retrieved.tls_verified:
            raise CalendarSourceAuthenticityError("TLS certificate validation failed")
        if retrieved.status_code != 200 or not retrieved.content:
            raise CalendarSourceAuthenticityError("Source artifact is unavailable or returned an invalid response")
        if retrieved.redirect_urls:
            raise CalendarSourceAuthenticityError("Redirects are not accepted for calendar source verification")
        if normalize_calendar_source_origin(retrieved.final_url) != expected_origin:
            raise CalendarSourceAuthenticityError("Final response origin does not match the exact approved origin")
