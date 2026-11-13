# EGX Session Calendar Activation — Design Gate

**Status:** GAP — bootstrap policy approved (Option 3); cursor contract and activation implementation remain open; HTTP activation remains intentionally unavailable  
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

**Important implementation gap:** the evaluator currently derives its per-opportunity cursor from the latest persisted completed-bar observation and otherwise starts from the immutable publication date. The repository does not yet expose a separate audited bootstrap-cursor record. Before activation can be implemented, the cursor's exact semantics and persistence boundary must be designed so that a bootstrap marker cannot be mistaken for a completed market observation or cause expiry/session counts to skip eligible sessions.

### Required bootstrap design before implementation

Detailed technical proposal: `docs/EGX-LIFECYCLE-BOOTSTRAP-CURSOR-DESIGN-PROPOSAL.md`. It proposes a per-opportunity append-only publication baseline distinct from a finality-verified reconciled-session cursor. This implementation detail still requires owner approval.

1. Define whether the durable cursor is per opportunity (recommended because lifecycle progress is opportunity-specific) and how immutable revisions inherit or reset it.
2. Define the cursor's semantic position: last fully reconciled eligible session, or an explicit pre-first-session baseline. Never conflate the two.
3. Define how the bootstrap process proves that every eligible session between the opportunity's lifecycle start and the cursor is reconciled, including how provider-finality failures and missing bars block cursor advancement.
4. Persist cursor state and append-only bootstrap audit evidence atomically; repeated bootstrap with the same inputs must be idempotent, and conflicting inputs must be rejected or require a new explicit review event.
5. Make activation validate that every active opportunity has a valid cursor and that the candidate calendar covers the cursor-derived horizon through the next scheduled evaluation date.
6. Keep activation, scheduled execution, and monitoring disabled until provider finality and the remaining deployment/E2E gates also pass.

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
- The evaluator derives a per-opportunity cursor from the latest persisted completed-bar observation and otherwise starts from publication date; a separate durable audited bootstrap-cursor record is not implemented. No scheduler is connected to the calendar.
- Provider finality attestation and per-day source evidence remain open.

**Gate result: Option 3 and cursor-derived coverage are owner-approved. Do not expose activation/deactivation/rollback over HTTP until the separate durable bootstrap-cursor contract is implemented, its persistence/recovery tests pass, and all provider/calendar/deployment gates are satisfied.**
