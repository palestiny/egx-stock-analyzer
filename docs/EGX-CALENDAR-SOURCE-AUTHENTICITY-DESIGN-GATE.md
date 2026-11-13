# EGX Calendar Source Authenticity — Approved Design Gate

**Status:** OWNER DECISIONS APPROVED — first implementation slice committed; activation gate not yet wired  
**Approved:** 2026-11-13  
**Related proposal:** `docs/EGX-CALENDAR-SOURCE-AUTHENTICITY-OWNER-DECISION-PROPOSAL.md`

## 1. Owner decisions

The owner explicitly approved:

- **Option B:** exact-origin trust registry plus independent human review.
- **Reviewer separation:** uploader and reviewer must be different named users and different durable credentials.
- **External-only evidence:** re-fetch the source at every activation decision and require byte-for-byte digest equality; otherwise fail closed.

Option A (publisher signatures) remains a possible stronger future method only if a real publisher signing mechanism and independently trusted key lifecycle are established. Option C is not sufficient by itself.

This approval does not approve any source origin, publisher endpoint, provider, calendar, activation, worker, monitoring, or external outreach.

## 2. Required trust model

Keep these assertions distinct:

1. **Byte integrity:** SHA-256 equality for exact artifact bytes.
2. **Origin authentication:** TLS-authenticated retrieval from an exact owner-approved HTTPS origin, with no redirects.
3. **Publisher binding:** the exact origin's owner-approved publisher/source-class/market-scope mapping.
4. **Claim review:** a different named operator verifies the exact artifact supports the exact evidence claim, date, class, and market scope.
5. **Retention permission:** a separate legal/operational decision; neither origin approval nor digest equality grants retention rights.

The approved-origin registry is exact-origin only: scheme + canonical hostname + standard HTTPS port. No wildcard hosts, implicit subdomains, HTTP, credentials in URLs, nonstandard ports, or unapproved redirects. Class A trust is limited to EGX operational claims; Class A-R is limited to FRA regulatory scope. B/C cannot become primary evidence through this registry.

## 3. Owner approval and operator accountability

- The SQLite origin registry is bound to a configured owner user ID.
- Approval/revocation requires that configured owner identity, an active durable credential, and operator permission supplied by authenticated application identity.
- Approval and revocation are append-only events. Re-approval creates a new registry version; it does not rewrite history.
- No origin is currently approved. The registry is intentionally empty until the owner separately names and approves an exact origin with a documented trust basis.
- Evidence creation now records the uploader's durable credential ID in addition to the immutable user ID. Legacy evidence without that credential ID cannot pass the independent-authenticity verifier.

## 4. Verification workflow

### Initial verification

1. Resolve the evidence URL to its canonical exact origin.
2. Find an active owner-approved origin record at the verification timestamp.
3. Require the configured publisher, source class, and market scope to match the evidence record.
4. Retrieve from that URL through a transport that validates TLS, does not follow redirects, and returns the exact bytes and final URL.
5. Require HTTP success, non-empty bytes, no redirects, exact-origin final URL, and SHA-256 equality with the evidence artifact digest.
6. For ARCHIVED evidence, read the archived object once through the verified-byte API and require its bytes to equal the bytes retrieved from the approved source.
7. Require a second individually authenticated operator to attest that the exact artifact supports the exact claim. The uploader and verifier must differ by both user ID and credential ID.
8. Append an immutable verification record containing evidence ID, decision, exact origin, trust-registry version, digest, uploader and verifier identities/credentials, claim digest, method version, timestamp, and reason.

### Activation-time revalidation

- The latest verification record must still match the evidence digest, claim digest, method version, and current origin-registry version.
- The origin must still be owner-approved and active, with publisher/class/scope still matching the evidence.
- ARCHIVED bytes must still pass storage integrity verification.
- EXTERNAL_ONLY evidence must be fetched again at decision time. Missing/unavailable content, TLS failure, redirects, changed bytes, or a changed trust approval blocks activation.
- Historical verification records are never rewritten. A new review or correction appends a new event.

## 5. Implemented in this slice

- `app/application/market_data/calendar_source_authenticity.py`: typed trust/verification records, strict URL-origin normalization, independent-operator checks, initial verification, archived-byte comparison, and EXTERNAL_ONLY activation-time re-fetch contract.
- `app/infrastructure/persistence/sqlite_calendar_source_origin_registry.py`: owner-bound exact-origin approval/revocation history with append-only triggers.
- `app/infrastructure/persistence/sqlite_calendar_evidence_verification_store.py`: append-only persisted verification outcomes.
- `CalendarEvidence.recorded_by_credential_id`: captures the uploader's durable credential for new evidence.
- `SQLiteCalendarEvidenceRepository`: additive nullable migration and canonical digest inclusion for new credential-bound records while preserving legacy record hashes.
- `CalendarArtifactService.read_verified`: reads the artifact once and returns bytes only after digest verification.
- Focused application and persistence tests were added for origin allowlisting, lookalike hosts, redirects, TLS failure, changed bytes, reviewer separation, re-fetch, owner-only trust changes, revocation, and immutable audit persistence.

## 6. Remaining blockers before this gate can pass

1. Implement and test the production HTTPS retriever. It must validate TLS, reject redirects, enforce response-size/time limits, and defend against DNS/IP-based SSRF; no unsafe generic URL fetcher may be used.
2. Wire the verifier and persisted verification store into the calendar activation validator so every unsuperseded Class A claim required by the evidence matrix must pass `revalidate_for_activation`. Missing verifier configuration must block activation.
3. Ensure evidence publication captures uploader credential provenance for every new operational evidence record; legacy records without it remain blocked until replaced through a new attributable evidence record.
4. Add an authenticated, owner-only review workflow for approving/revoking exact origins and a separate reviewer workflow for claim review. Do not expose a route until owner identity and reviewer credential checks are proven in runtime composition.
5. Add exact-head tests for the complete production composition and prove a missing/unapproved origin or missing verification record leaves active calendar pointer and activation audit unchanged.
6. Define and verify deployment configuration for the retriever, durable origin registry, verification store, and artifact storage.

No origin is approved by this design. Therefore the verifier has no usable production trust anchor today.

## 7. Operational boundary

- No EGID or other provider was contacted; no outreach is authorized.
- No source origin/domain is approved by this decision.
- No automatic scraping or ingestion is enabled.
- No calendar activation endpoint or runtime route is added by this slice.
- No calendar is activated; no lifecycle worker or monitoring is enabled.
- Provider Finality remains an independent activation blocker.
- PR #515 remains Draft and must not be merged or marked ready without explicit owner approval.

**Gate result:** PARTIAL IMPLEMENTATION — NOT READY FOR ACTIVATION.
