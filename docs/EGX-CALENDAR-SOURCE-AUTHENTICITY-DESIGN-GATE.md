# EGX Calendar Source Authenticity — Approved Design Gate

**Status:** OWNER DECISIONS APPROVED — verifier, refetch transport, activation preflight, owner trust API, and separate reviewer API implemented; production trust anchors remain empty  
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

- `app/application/market_data/calendar_source_authenticity.py`: typed trust/verification records, strict URL-origin normalization, independent-operator checks, initial verification, archived-byte comparison, EXTERNAL_ONLY activation-time re-fetch, and explicit VERIFIED/REJECTED reviewer outcomes.
- `app/infrastructure/persistence/sqlite_calendar_source_origin_registry.py`: owner-bound exact-origin approval/revocation history with append-only triggers.
- `app/infrastructure/persistence/sqlite_calendar_evidence_verification_store.py`: append-only persisted verification outcomes; uploader and reviewer must both retain active individual operator credentials.
- `app/infrastructure/market_data/https_calendar_source_artifact_retriever.py`: direct HTTPS retrieval with certificate validation, pinned public-IP connection, mixed/private DNS answer rejection, no implicit redirects, bounded response size, and connection timeout.
- `app/infrastructure/persistence/sqlite_calendar_evidence_uploader_identity_resolver.py` and `app/application/market_data/review_calendar_evidence_authenticity.py`: resolve the original uploader from immutable evidence provenance and require a different active operator to review.
- `app/api/calendar_source_authenticity_routes.py`: owner-only exact-origin approve/revoke/audit endpoints and a separate individual-operator evidence-review endpoint. There is no calendar activation endpoint in this router.
- Runtime composition creates these services only when `EGX_CALENDAR_SOURCE_TRUST_OWNER_USER_ID` is explicitly configured. The variable is unset by default; no origin is seeded or pre-approved.
- Activation validator performs external re-fetch before the coordinator's SQLite write transaction, then checks the persisted preflight proof and current trust-registry version inside the atomic transaction. Failed preflight cannot change the active pointer or activation audit.
- `CalendarEvidence.recorded_by_credential_id`: captures the uploader's durable credential for new evidence.
- `SQLiteCalendarEvidenceRepository`: additive nullable migration and canonical digest inclusion for new credential-bound records while preserving legacy record hashes.
- `CalendarArtifactService.read_verified`: reads the artifact once and returns bytes only after digest verification.
- Focused application and persistence tests were added for origin allowlisting, lookalike hosts, redirects, TLS failure, changed bytes, reviewer separation, re-fetch, owner-only trust changes, revocation, and immutable audit persistence.

## 6. Remaining blockers before this gate can pass

1. Set the configured owner identity explicitly in deployment only after confirming the intended owner account; until then `EGX_CALENDAR_SOURCE_TRUST_OWNER_USER_ID` remains unset and trust-management routes are not composed.
2. The owner must separately approve each exact origin with a documented trust basis. The registry is empty by default; engineering has not approved EGX, FRA, subdomains, or any vendor domain.
3. The production-runtime composition path is now covered by an end-to-end API test using the real durable bearer-token authenticator, operator grant store, SQLite evidence repository, owner origin registry, verification store, uploader identity resolver, and reviewer route. The test injects a deterministic fake retriever to avoid network I/O. A separate deployment-environment transport validation and a full activation-coordinator integration test (real validator + real SQLite verifier + atomic active-pointer/audit transaction) remain outstanding. The runtime test now directly exercises real SQLite-backed revalidate_for_activation and assert_preflight_verification, including changed-byte rejection and stale-proof rejection; it does not yet prove the coordinator's complete transaction boundary.
4. Validate the HTTPS retriever against the deployment's outbound network policy and TLS/proxy environment without contacting EGID or any data provider as part of this work.
5. Establish source-specific retention/reuse permission and deployment backup/restore/capacity procedures. Authenticity does not grant legal retention rights.
6. Keep Provider Finality, calendar bootstrap/recovery, deployment recovery, and exact-head CI as independent activation blockers.

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


## 8. Follow-up implementation status — 2026-11-13

- The approved Option-B design is now represented end-to-end in application services and persistence: owner-governed exact-origin trust, independent reviewer identity resolution, immutable VERIFIED/REJECTED decisions, direct bounded HTTPS refetch, and activation-time proof checking.
- Owner trust routes are composed only when an explicit owner UUID is configured. The default runtime leaves them absent and the trust registry empty. No production owner UUID or source origin has been configured by this change.
- The independent reviewer route is available to a different individually authenticated operator; the application resolves the original uploader from immutable evidence provenance rather than accepting uploader identity from the request.
- Origin approval/revocation events are append-only, owner-attributed, serialized with BEGIN IMMEDIATE, and reject duplicate active approvals or out-of-order event timestamps.
- The activation preflight performs network retrieval outside the activation write transaction; the transaction then verifies the matching preflight record, evidence digest/claim digest, exact source origin, and current trust version. This implementation does not expose an activation API.
- Tests cover the reviewer and owner API boundaries, uploader/reviewer separation, rejection records, exact-origin matching, trust event ordering, bounded HTTPS transport, and empty-by-default runtime composition.

**Current result:** IMPLEMENTATION SLICE COMPLETE IN CODE; production authenticity is NOT ESTABLISHED because no origin has been approved and no actual EGX evidence has been independently reviewed. No provider outreach, calendar activation, worker, or monitoring is authorized or enabled. Exact-head CI remains the final verification for the current code head.


## 9. Production composition integration test — 2026-11-13

The runtime integration test now exercises the complete review path without contacting a real publisher:
1. Compose the real runtime with an explicit test owner UUID.
2. Authenticate owner, uploader, and reviewer through durable bearer credentials and persisted individual-operator grants.
3. Approve an isolated fixture origin through the owner-only HTTP endpoint.
4. Publish a calendar and evidence through the normal calendar publication endpoint, binding the uploader's immutable user and credential IDs.
5. Submit the independent review through the operator HTTP endpoint; the application resolves the uploader from persisted evidence provenance.
6. Persist and read back the VERIFIED decision through the real SQLite verification store.
7. Confirm a non-owner and the legacy shared token cannot read owner trust events.

The retriever is replaced only inside this isolated test with deterministic fixture bytes. It does not establish trust in any real EGX origin, validate deployment outbound networking, or exercise the activation coordinator. Those remain separate gates.


## 10. SQLite-backed activation preflight verification — 2026-11-13

The runtime integration test now goes beyond initial human review:
- It loads persisted evidence through the real SQLite evidence repository.
- It invokes the real verifier backed by the SQLite origin registry and append-only verification store.
- It confirms external-only bytes are re-fetched and a fresh VERIFIED proof is persisted at the exact preflight timestamp.
- It confirms the transaction-side assert_preflight_verification accepts that exact proof.
- It changes deterministic retriever bytes and confirms the next preflight rejects the changed digest.
- It confirms the stale successful proof cannot satisfy the failed preflight's later timestamp.

This is a verifier/persistence preflight integration test, not a full activation-coordinator integration test. It does not activate a calendar or change an active pointer.
