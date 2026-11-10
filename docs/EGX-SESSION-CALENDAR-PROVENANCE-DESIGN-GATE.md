# EGX Session Calendar Provenance & Operator Accountability — Design Gate

**Status:** D1–D4 POLICY APPROVED — enforcement under PR #475; activation remains blocked  
**Reviewed:** 2026-11-10  
**Related:** PR #459, #460, #465, #466, #467

## 1. Owner decisions

The owner approved:
- **B — Immutable per-day evidence registry**
- **B — Individual named operator principals**
- **D1 — Source classes A / A-R / B / C:** A is primary EGX operational evidence; A-R is FRA regulatory evidence within its regulatory scope; B and C are corroboration only.
- **D2 — Hybrid artifact retention (Option C):** archive exact source bytes when permitted and operationally supportable; otherwise preserve a stable reference, artifact digest, retrieval metadata, and an explicit non-retention reason.
- **D3 — Strict evidence-gated publication:** a published calendar version must satisfy the accepted evidence matrix; incomplete candidates remain unpublished.
- **D4 — Per-claim evidence matrix in Section 3:** no inferred closure, opening, session completion, or exceptional hours.

PR #475 implements the approved evidence policy. Approval does not establish source authenticity, artifact legality, deployment readiness, or calendar activation.

The approved decisions are implemented in part:
- PR #465 adds append-only, hash-verified evidence records keyed by calendar version, session date, and evidence kind. Corrections are new records with explicit supersession and reason.
- PR #466 adds individual operator grants, append-only grant/revoke/bootstrap events, a local first-operator bootstrap command, and durable-credential-aware permission resolution.
- PR #467 is merged and requires an active individual operator identity (user ID plus durable credential ID) for calendar administration; it rejects the synthetic shared operator identity.

## 2. Per-day evidence registry — implemented boundary

The current evidence record includes:
- Stable evidence ID and calendar version.
- Explicit session date and typed evidence kind.
- Source type/reference and a concise claim.
- Recorded-by user ID.
- Observed-at, recorded-at, and optional source-published-at timestamps.
- Optional superseded evidence ID and mandatory supersession reason.
- Canonical SHA-256 digest checked on read.

Persistence is append-only: database triggers reject UPDATE and DELETE. Conflicting unsuperseded claims of the same kind/day remain visible. A superseding record preserves the prior evidence history.

**Publication enforcement (merged in PR #471; exact-head CI passed):** the publication API now requires immutable evidence for every explicit calendar date, validates evidence kinds against the calendar-day status, creates explicit day-to-evidence links, and rejects unresolved conflicting claims inside the same SQLite transaction. The registry and publication gate still do not independently prove source authenticity or preserve the source artifact.

## 3. Approved evidence acceptance rules

- Class A EGX operational evidence is required for primary EGX-wide calendar claims.
- Class A-R FRA evidence may explain the regulatory basis within FRA's scope but cannot replace the EGX operational notice where an operational session claim is made.
- Class B and C sources are corroboration only and cannot independently authorize a calendar date or session time.
- NON_TRADING requires explicit Class A closure/non-trading evidence; never infer from weekday or national holiday.
- SCHEDULED requires Class A schedule evidence covering the exact date and market scope.
- OPEN requires Class A schedule evidence plus Class A operational opening confirmation.
- CANCELLED requires Class A cancellation/suspension evidence.
- CLOSED requires Class A schedule evidence plus Class A close/market-status confirmation supporting the close timestamp.
- Exceptional/shortened hours require an explicit calendar-day marker and Class A EXCEPTIONAL_HOURS evidence. Ordinary schedule evidence is preserved separately where needed.
- Emergency closure/reopening requires Class A evidence with affected date and effective time; FRA evidence may explain but not replace the operational notice.
- Evidence must match the affected date and market scope. Evidence for an index or one market segment is not automatically evidence for every EGX segment.
- Hybrid retention records whether bytes are archived or external-only. A digest without retained or independently retrievable bytes is not proof of source authenticity.
- Conflicting claims remain unresolved until superseded by a documented correction. Incomplete candidates remain unpublished.


## 4. Individual operator access — implemented boundary

The operator access model uses named application users with an explicit `OPERATOR` permission derived from an active grant and an active durable bearer credential.

- Grant/revoke operations require an individually authenticated operator and record actor user ID, actor credential ID, target user ID, reason, and timestamp.
- The event history is append-only.
- First-operator bootstrap is a one-time local administrative command for an active user with an active durable credential. The event is marked as a system bootstrap, not falsely attributed to a person.
- The last active operator cannot be revoked or disabled.
- Disabling/deleting an operator automatically revokes the grant; reactivation does not silently restore it.
- The legacy shared operator token remains for compatibility with unrelated legacy operator routes, but calendar administration rejects it.

## 5. Remaining engineering and operational acceptance

- Complete PR #475 exact-head CI and merge only after all five required jobs pass.
- Verify additive SQLite migration against a representative pre-policy evidence database and preserve legacy record-digest verification.
- Verify API-level rejection for missing/invalid source and retention metadata, plus atomic rollback on every policy rejection.
- Independently verify archived artifact bytes against artifact_sha256; current operator-supplied digest/reference fields do not authenticate the publisher or artifact.
- Verify first-operator bootstrap and recovery against the actual deployment database and operational procedure.
- Close cursor-derived activation coverage/bootstrap and provider completed-bar attestation gates independently.
- Keep activation and lifecycle monitoring disabled until every relevant gate passes.

## 6. Current boundary

Calendar publication remains separate from activation. No calendar has been activated, and lifecycle monitoring remains disabled. No schedule, weekend, holiday, or session time is inferred. Provider completed-bar attestation and cursor-derived coverage validation remain independent activation blockers.

**Gate result:** immutable evidence storage, individual operator identity, atomic per-day evidence linkage, completeness/status-kind validation, and conflict rejection are merged in PR #471. Its exact head passed all five CI jobs. The latest main CI after PR #472 is tracked in CURRENT_STATE.md. Source-class acceptance, artifact retention/authenticity, and operational activation gates remain open.


## 10. Atomic publication implementation — PR #471

- A calendar-specific SQLite Unit of Work uses one `BEGIN IMMEDIATE` transaction for the immutable calendar version, evidence records, explicit day/evidence links, and conflict validation.
- The API requires evidence for every explicit date and validates the minimum evidence kind implied by each day status: closure, cancellation, schedule, and close confirmation for a completed session.
- Evidence corrections can be supplied in order within the same publication batch using caller-provided stable evidence IDs and supersession references; originals remain immutable.
- Rollback tests inject failures after evidence insertion and after link creation/final validation. A separate SQLite connection is verified not to observe uncommitted publication rows.
- PR #471 merged at `bad0f1b134586fd6ffe32ebf09352c31a5fb445f`; its exact head passed all five required CI jobs. The latest post-merge main CI after PR #472 is still tracked separately.
- Source authenticity and deployment-level artifact verification remain outside PR #471. PR #475 implements source-class acceptance, hybrid retention metadata, and claim-specific evidence enforcement; activation bootstrap and lifecycle integration remain separate gates.


## 11. Post-merge status — 2026-11-10

PR #471 is merged. The atomic publication implementation and its rollback/isolation/runtime tests passed all five exact-head CI jobs. PR #472 subsequently updated the market-history archive; its exact-head CI passed all five jobs. The latest main-line CI is run #42855711113 on `b2fa65e4ffa68cb80c27bad6e69da45e03fe126a`; four jobs have passed and unit tests remain in progress. D1–D4 policy is owner-approved and PR #475 is the enforcement implementation. Source authenticity, deployment artifact verification, bootstrap/recovery, cursor-derived activation coverage, and provider finality remain open. No calendar has been activated. No calendar has been activated.
