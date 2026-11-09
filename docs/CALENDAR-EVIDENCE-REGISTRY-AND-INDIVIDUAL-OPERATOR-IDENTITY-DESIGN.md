# EGX Calendar Evidence Registry and Individual Operator Identity

**Status:** OWNER-APPROVED DESIGN — implementation and acceptance remain open  
**Approved:** 2026-11-09  
**Related:** DEC-139, EGX-SESSION-CALENDAR-IMPLEMENTATION-CONTRACT.md, MARKET-DATA-PROVIDER-RELIABILITY-DESIGN-GATE.md  
**Scope:** Auditable evidence for calendar-day decisions and attributable operator actions. This gate does not authorize calendar activation or lifecycle monitoring.

## 1. Owner decisions

The owner approved:

1. An immutable evidence registry: evidence is append-only; corrections and superseding evidence create new records and never rewrite prior evidence.
2. Individual operator identities: every privileged calendar action must be attributable to a distinct authenticated human account, not a shared operator subject or shared bearer token.

These are architectural decisions. This document does not assert that the implementation is already complete.

## 2. Current verified boundary

The current calendar persistence adapter stores immutable, SHA-256-verified calendar versions and append-only activation/deactivation/rollback events. Calendar version metadata has one source_reference, publication timestamp, reason, and published_by string. It does not yet provide a structured, per-session-day evidence registry.

The current authentication model already has users and durable credentials. However, the compatibility path can still authenticate a configured legacy operator token and returns the synthetic operator identity. That identity is not attributable to an individual person. Existing user/credential primitives are a foundation, not proof that all privileged routes enforce named operator accounts.

## 3. Immutable calendar evidence model

Introduce a domain record with, at minimum:

- evidence_id: stable unique identifier;
- calendar_version and session_date: exact version/day being supported;
- evidence_kind: schedule, closure, cancellation, exceptional-hours, or close-confirmation;
- source_type: official exchange notice or another explicitly classified source;
- source_reference: durable URL/document/reference identifier;
- source_published_at: source publication timestamp when known;
- observed_at: when the operator/system obtained the evidence;
- recorded_at: server-generated timezone-aware UTC timestamp;
- recorded_by: immutable individual operator user ID;
- claim / structured_payload: the precise calendar fact supported;
- content_sha256: hash of canonical evidence metadata/payload;
- supersedes_evidence_id: optional link to an earlier record;
- supersession_reason: mandatory when superseding prior evidence.

Evidence rows must be append-only at the database boundary (UPDATE and DELETE rejected by triggers). A correction is a new row that points to the prior row. The original evidence remains queryable. Hash verification must run when reading evidence, not only when inserting it.

A calendar day may have multiple evidence records. Conflicting claims must remain visible and unresolved; the system must not silently choose one source or overwrite the earlier record. A day can be considered sufficiently evidenced only under a separately documented acceptance policy that identifies which source classes and evidence combinations are authoritative.

## 4. Provenance and publication rules

- A calendar version must link to its day-level evidence records, not merely a single free-form source string.
- Every trading-day status, session-hours override, cancellation, and closed_at confirmation must reference supporting evidence.
- Publication must fail if required day-level evidence is absent or has unresolved conflicts under the approved evidence policy.
- Evidence must distinguish source publication time, operator observation time, and system recording time.
- External references are not proof by themselves: retain the retrieved document or a durable content snapshot/hash where legally permitted.
- Never fabricate an official source, infer an EGX holiday from a national holiday, or infer a session close from a weekday schedule.
- Calendar versions and evidence remain immutable after publication.

## 5. Individual operator identity and authorization

- Every privileged operator is a distinct active application user with an individual durable credential.
- Authentication for calendar publication, activation, deactivation, and rollback must resolve to that user's immutable ID and credential ID.
- Authorization must verify an explicit operator permission/role; being an authenticated application user is not sufficient.
- Audit events store the immutable user ID, credential ID (where applicable), action, target, previous value, reason, and server-generated timestamp.
- Shared legacy operator credentials must not authorize privileged calendar operations once the migration gate is closed.
- Do not silently map the legacy synthetic operator subject to a real person.
- Credential issuance, rotation, revocation, disabled-user handling, and recovery must be tested.
- Preserve a controlled bootstrap/recovery path that does not create a permanent shared credential. Its operational owner and recovery procedure must be documented before legacy access is disabled.

## 6. Migration and rollout sequence

1. Add evidence domain types, canonical serialization, validation, and immutable SQLite storage.
2. Add append-only correction/supersession and conflict-query behavior.
3. Add tests for hash tampering, update/delete rejection, duplicate evidence, conflicting evidence, supersession, restart persistence, and timezone handling.
4. Add explicit operator role/permission assignment and ensure privileged routes reject the legacy synthetic identity.
5. Add operator audit identity/credential linkage to all calendar privileged events.
6. Provide an audited bootstrap path for the first individual operator; verify recovery and credential rotation.
7. Backfill no historical evidence automatically. Existing calendar versions remain published metadata without retroactively invented per-day provenance until evidence is actually supplied.
8. Add publication validation against the evidence policy and test it end to end.
9. Only after separate acceptance may an owner-reviewed calendar be activated. Activation still requires verified operational coverage and provider-completed-bar evidence.

## 7. Acceptance criteria

- Every published session-day claim has one or more immutable evidence references.
- Evidence payload/hash tampering is detected on read.
- UPDATE/DELETE attempts fail at the database layer.
- Conflicts remain visible and block publication where the evidence policy requires resolution.
- Corrections append a new record and preserve the original.
- Audit records identify a real individual user and credential, not operator.
- Missing, revoked, expired/disabled, or unauthorized credentials cannot perform privileged calendar actions.
- No privileged route silently falls back to the shared legacy token.
- Bootstrap/recovery does not require a permanent shared operator token.
- Restart/replay is deterministic and idempotent.
- Calendar activation and lifecycle monitoring remain disabled until their independent data, coverage, and operational gates pass.

## 8. Explicit non-goals

This approval does not select an EGX calendar source, declare any specific date a holiday or trading day, approve a market-data provider, establish provider bar finality, activate a calendar, enable Crash Radar freshness enforcement, enable lifecycle monitoring, or resume M61/backtesting.

## 9. Implementation progress (2026-11-09)

The first persistence slice is now present on the PR branch:

- Typed evidence records cover schedule, closure, cancellation, exceptional-hours, and close-confirmation claims.
- SQLite stores evidence against an existing immutable calendar version and an explicitly represented date inside that version's coverage.
- Database triggers reject evidence UPDATE and DELETE operations.
- Canonical SHA-256 hashes cover the evidence identity, day, source, claim, actor ID, and timestamps; reads re-compute and verify the hash.
- Corrections append a new record linked to the prior record with a mandatory reason. The original remains retrievable.
- Conflicting unsuperseded claims of the same evidence kind are returned as conflicts; superseded records remain in the audit history but do not create an active conflict by themselves.
- Focused persistence tests have been added. Their exact-head CI result is pending; no test pass is claimed yet.

Still not implemented: publication/API enforcement of evidence completeness and conflict resolution; database-level verification that recorded_by is an active, authorized operator; operator role assignment and bootstrap/recovery; linking activation events to credential IDs; and end-to-end authorization tests. The evidence hash is an integrity check, not a digital signature or proof that the external source is authentic.
