# EGX Session Calendar Activation — Design Gate

**Status:** IMPLEMENTATION SLICE COMPLETE — bootstrap and atomic activation coordinator exist; operational activation remains blocked; no HTTP activation route  
**Reviewed:** 2026-11-13  
**Related decisions:** DEC-135, DEC-138, DEC-139  
**Scope:** Preconditions for activating, deactivating, or rolling back an immutable EGX session-calendar version.

## 1. Problem

The domain model and SQLite repository can represent explicit calendar versions, one active-version pointer, and append-only activation/deactivation/rollback events. PR #467 merged the individually authenticated operator API for publishing and inspecting versions, but it does not expose activation.

Activating a syntactically valid calendar without proving that it covers the dates the runtime must evaluate could cause the lifecycle monitor to skip or misclassify sessions. A coverage policy must be defined before activation becomes an HTTP operation.

## 2. Accepted constraints

- The calendar uses Africa/Cairo and contains one explicit, ordered record for every date in its declared coverage.
- Missing dates and out-of-range requests fail closed; the system must not infer weekends or holidays.
- Only a date explicitly marked CLOSED, with a timezone-aware closed_at confirmation, is a completed EGX session.
- DEC-139 schedules lifecycle evaluation after the configured session close plus 60 minutes and requires chronological reconciliation of eligible sessions since the durable cursor.
- Calendar activation is not provider-completion attestation. A calendar cannot prove that a provider's daily OHLC bar is final or complete.
- Activation, deactivation, and rollback must be auditable and performed by an authenticated operator.
- The current legacy operator token maps to the shared subject `operator`; it does not establish individual human attribution. Named operator identities or another approved attributable mechanism are required before production operations.

## 3. Coverage-horizon options

| Option | Rule | Trade-off |
|---|---|---|
| Fixed forward buffer | Require a fixed number of future calendar days (for example, 30). | Simple, but the number is arbitrary and does not prove missed-session recovery coverage. |
| Full calendar year | Require the candidate to cover the whole calendar year. | Easy to reason about, but can reject valid rolling updates and still does not establish the correct recovery cursor. |
| Cursor-derived horizon | Require explicit coverage from the durable evaluation cursor through the next scheduled evaluation date. | Matches DEC-139 recovery semantics and avoids an arbitrary day count; requires a durable cursor and an explicit bootstrap rule. |

### Approved coverage rule — cursor-derived horizon

The owner approved the cursor-derived horizon. The candidate calendar must cover every explicit date after the durable evaluation cursor through the next scheduled evaluation date, without gaps. A previously active calendar version is not automatically safe for rollback; revalidate it against the current cursor.

### Recommendation — approved

Use a cursor-derived horizon rather than a hard-coded 30-day or full-year rule:

1. Let C be the last durably reconciled EGX session date (exclusive).
2. Let N be the next session date that the scheduler may evaluate, determined only from explicit calendar records.
3. Require the candidate calendar to cover every date from C + 1 through N, inclusive, with no gaps.
4. Require the candidate to preserve explicit status and session-time records for all dates in that interval. A SCHEDULED or OPEN date is not a completed session.
5. Re-run the same check for rollback targets; a historically active version is not automatically safe for the current cursor.

This rule ties coverage to the work the runtime must perform. It deliberately does not prescribe a fixed forward buffer.

## 4. Approved bootstrap decision — Option 3

**Owner decision (2026-11-13): No activation until a durable cursor exists.** The owner explicitly rejected implicit activation from the machine's current date and unbounded calendar-start backfill.

Consequences:

- Calendar activation remains blocked until a controlled bootstrap process has created the required durable lifecycle evaluation cursor(s).
- A cursor must have an explicit, auditable provenance and be persisted; an in-memory value, a scheduler timestamp, or the mere existence of an active calendar is not a cursor.
- Bootstrap must not silently skip prior eligible sessions, declare them reconciled, or imply provider finality. Calendar activation and cursor creation do not attest that market bars are final.
- Bootstrap must be idempotent, restart-safe, attributable to an individually authenticated operator or approved system principal, and fail closed on missing calendar/source evidence.
- No date may be inferred from the host clock, weekends, holidays, or a guessed provider availability window.

**Superseded implementation note:** the original cursor gap described below was closed by the approved PUBLICATION_BASELINE / RECONCILED_SESSION design and its implementation on PR #515. The evaluator now requires persisted bootstrap evidence for the exact opportunity revision and calendar version; the baseline is derived from immutable publication history and remains distinct from completed-bar observations. The effective reconciled cursor still comes only from committed, finality-verified observations. The baseline is not counted toward expiry.

### Implemented bootstrap contract

The owner-approved proposal is implemented on PR #515. See `docs/EGX-LIFECYCLE-BOOTSTRAP-CURSOR-DESIGN-PROPOSAL.md` and `docs/EGX-LIFECYCLE-BOOTSTRAP-CURSOR-OWNER-DECISION.md` for the decision and implementation record.

- `PUBLICATION_BASELINE` and `RECONCILED_SESSION` remain distinct; no synthetic bar is created.
- Bootstrap is per immutable opportunity revision, append-only, idempotent, and persisted in an all-or-nothing batch.
- The baseline and publication provenance are derived from immutable publication history in `Africa/Cairo`.
- Candidate calendar coverage is checked explicitly through a trusted next-evaluation date; the request cannot supply that date.
- The activation validator checks candidate publication/integrity, active latest revisions, bootstrap batch/record integrity, explicit coverage, next-session status, and reconciled-cursor compatibility.
- A calendar-backed evaluation-schedule adapter and SQLite activation coordinator serialize validation, active-pointer mutation, and append-only activation audit in one SQLite transaction.

These are code capabilities only. They do not approve a real source origin, publish/activate a production calendar, or authorize worker/monitoring enablement.

No implementation should create a synthetic completed-bar observation, mark old sessions as reconciled without evidence, or use a guessed date to satisfy the activation gate.

## 5. Activation transaction and API prerequisites

Before adding activation endpoints, implement and test:

1. **Implemented at repository boundary:** verify the target version exists and its persisted content hash passes integrity validation inside the activation transaction. A corrupt target is rejected without changing the active pointer or audit history.
2. Validate the target against the approved coverage-horizon and bootstrap policy.
3. Ensure the candidate is not missing any explicit date in the required interval.
4. Require an authenticated operator identity and a non-empty reason; never accept the actor identity from the request body.
5. Change the active-version pointer and append the ACTIVATE/ROLLBACK event in one SQLite BEGIN IMMEDIATE transaction.
6. For deactivation, atomically clear the pointer and append a DEACTIVATE event. Do not silently fall back to an older version.
7. On any validation or persistence failure, leave the active pointer and audit history unchanged.

## 6. Required tests

- Candidate missing the cursor date, an intermediate date, or the next scheduled evaluation date is rejected.
- Candidate containing explicit NON_TRADING, SCHEDULED, OPEN, CLOSED, and CANCELLED records is interpreted according to status; no status is inferred from weekday.
- A CLOSED date without timezone-aware closed_at, or with confirmation before the configured close, is rejected by the domain model.
- A rollback target that was previously active but no longer covers the current cursor-derived horizon is rejected.
- Initial activation is rejected until a controlled, durable, audited bootstrap cursor exists for every in-scope active opportunity.
- Failed activation and rollback preserve the prior active pointer and append no misleading success event.
- Concurrent activation attempts serialize; the final pointer and audit events remain consistent.
- Actor identity comes from the authenticated principal, and non-operators receive 403. The publication API test verifies that blank subjects are rejected and client-supplied actor values are forbidden.
- Individual operator accountability is implemented for calendar administration by PR #466/#467. Deployment bootstrap/recovery verification remains open.
- Activation does not mark provider bars final, does not enable lifecycle monitoring by itself, and does not change Crash Radar scoring.

## 7. Current implementation boundary

- Immutable calendar persistence, content-hash verification on reads and before activation/rollback, active pointer, and append-only audit-event primitives are implemented. A regression test proves a corrupt version cannot be activated.
- Authenticated publication and read endpoints merged in PR #467. They derive the actor from the active individual operator principal; the shared legacy operator identity is rejected.
- No real EGX calendar version is published or active.
- The evaluator requires a persisted append-only bootstrap record for each active latest opportunity revision and uses the latest committed completed-bar observation as the reconciled cursor when one exists. No real EGX calendar is active and no scheduled worker is connected.
- Provider finality attestation and per-day source evidence remain open.

**Gate result: bootstrap persistence, cursor-derived validation, and the provider-neutral atomic SQLite activation coordinator are implemented on PR #515. Operational calendar activation remains BLOCKED: there is no approved exact source origin, no independently reviewed real EGX evidence, no production deployment validation/backup-restore proof, and no accepted provider finality. No HTTP activation endpoint or operational activation command is exposed. Do not activate, wire the worker, enable monitoring, or merge PR #515 until all independent gates pass and the owner explicitly authorizes the action.**
