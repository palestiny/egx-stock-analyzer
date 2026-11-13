# Owner Decision — EGX Lifecycle Bootstrap Cursor

**Decision date:** 2026-11-13  
**Status:** APPROVED  
**Applies to:** PR #515, opportunity lifecycle calendar activation, and scheduled-worker readiness  
**Related design:** `docs/EGX-LIFECYCLE-BOOTSTRAP-CURSOR-DESIGN-PROPOSAL.md`

## Decision

The owner approves the proposed **PUBLICATION_BASELINE / RECONCILED_SESSION** split and the append-only, per-opportunity bootstrap-record design.

This approval makes the proposal's semantics and persistence contract the accepted design baseline. It does not approve calendar activation, provider selection, provider outreach, scheduled-worker enablement, or production monitoring.

## Accepted semantics

1. `PUBLICATION_BASELINE` is an exclusive lower bound derived from the immutable publication event for the exact opportunity/revision identity, using `Africa/Cairo`. It proves no market session was reconciled and is not a candle or an eligible session.
2. `RECONCILED_SESSION` is the latest session whose completed daily bar passed provider finality verification and whose observation, lifecycle state/history, and alert-outbox intent committed atomically.
3. The effective cursor is the latest `RECONCILED_SESSION`, or the publication baseline when no reconciled observation exists.
4. Every session after the effective cursor is reconciled chronologically. A missing, stale, rejected, provisional, malformed, future, or unverified bar does not advance the cursor. Processing stops at the first required gap.
5. The baseline is never counted toward the 20-eligible-session expiry rule. Existing publication-date-exclusive behavior is preserved.
6. Each immutable opportunity/revision has its own cursor identity. Parent and child revisions do not share mutable progress.
7. Bootstrap records and batch audit results are append-only, attributable, restart-safe, and idempotent. Conflicting replay is rejected; no partial batch may be treated as activation-ready.
8. A new publication must receive its baseline atomically with publication, or through a verified pre-evaluation bootstrap path. An opportunity without a valid baseline is ineligible for worker evaluation.
9. Calendar activation must validate every active opportunity's baseline and explicit candidate-calendar coverage through the next scheduled evaluation date. Rollback repeats the same validation against current cursors.
10. Bootstrap metadata must never be represented as a synthetic completed-bar observation or used to imply provider finality.

## Implementation and release boundaries

- Implement the domain/application contract, persistence, migrations, API/operator workflow if required, and tests against deterministic test doubles.
- Preserve backward compatibility. Do not synthesize historical bootstrap records or mutate existing observation evidence during migration.
- Keep calendar activation endpoints unavailable and the worker disabled until provider finality, evidence-backed calendar, attributable operator, deployment recovery, exact-head CI, and full E2E gates pass.
- No provider outreach, quote/account/credential request, or provider selection is authorized. EGID remains research-only.
- Do not activate production monitoring or merge PR #515 on the basis of this decision alone.

## Required acceptance evidence

- Correct Cairo-local baseline derivation from immutable publication history.
- Missing/ambiguous publication history fails closed.
- Distinct revision cursors and no cross-revision advancement.
- Baseline excluded from session counts and expiry.
- Observation commit advances effective cursor atomically; failures do not.
- Gaps and all ineligible bars preserve cursor position.
- Idempotent bootstrap, conflict rejection, concurrent duplicate safety, and all-or-nothing batch behavior.
- Restart recovery and backward-compatible SQLite migration.
- New-publication baseline creation is atomic or proven before eligibility.
- Calendar activation and rollback reject missing baselines or any uncovered explicit date.
- Authenticated actor is derived from the principal, never request payload.
- Exact-head CI passes; all production gates remain independently enforced.

## Next execution order

1. Inspect existing lifecycle domain, Unit of Work, SQLite schema/repositories, publication transaction, and calendar activation boundary; map reusable components before editing.
2. Implement the smallest compatible append-only bootstrap contract and persistence migration.
3. Add application workflow and atomic batch audit with authenticated actor provenance.
4. Integrate publication-time baseline creation or the explicitly tested pre-evaluation path.
5. Add activation coverage validation without exposing or enabling activation prematurely.
6. Add failure, concurrency, restart, revision, and migration tests; run full exact-head CI.
7. Update design gates and PR #515 with verified evidence only.

**Owner approval recorded. Implementation is not yet claimed complete.**
