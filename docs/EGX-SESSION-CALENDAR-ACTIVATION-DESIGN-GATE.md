# EGX Session Calendar Activation — Design Gate

**Status:** GAP — activation policy is not approved; HTTP activation remains intentionally unavailable  
**Reviewed:** 2026-11-09  
**Related decisions:** DEC-135, DEC-138, DEC-139  
**Scope:** Preconditions for activating, deactivating, or rolling back an immutable EGX session-calendar version.

## 1. Problem

The domain model and SQLite repository can represent explicit calendar versions, one active-version pointer, and append-only activation/deactivation/rollback events. The operator API can publish and inspect versions, but it does not expose activation.

Activating a syntactically valid calendar without proving that it covers the dates the runtime must evaluate could cause the lifecycle monitor to skip or misclassify sessions. A coverage policy must be defined before activation becomes an HTTP operation.

## 2. Accepted constraints

- The calendar uses Africa/Cairo and contains one explicit, ordered record for every date in its declared coverage.
- Missing dates and out-of-range requests fail closed; the system must not infer weekends or holidays.
- Only a date explicitly marked CLOSED, with a timezone-aware closed_at confirmation, is a completed EGX session.
- DEC-139 schedules lifecycle evaluation after the configured session close plus 60 minutes and requires chronological reconciliation of eligible sessions since the durable cursor.
- Calendar activation is not provider-completion attestation. A calendar cannot prove that a provider's daily OHLC bar is final or complete.
- Activation, deactivation, and rollback must be auditable and performed by an authenticated operator.

## 3. Coverage-horizon options

| Option | Rule | Trade-off |
|---|---|---|
| Fixed forward buffer | Require a fixed number of future calendar days (for example, 30). | Simple, but the number is arbitrary and does not prove missed-session recovery coverage. |
| Full calendar year | Require the candidate to cover the whole calendar year. | Easy to reason about, but can reject valid rolling updates and still does not establish the correct recovery cursor. |
| Cursor-derived horizon | Require explicit coverage from the durable evaluation cursor through the next scheduled evaluation date. | Matches DEC-139 recovery semantics and avoids an arbitrary day count; requires a durable cursor and an explicit bootstrap rule. |

### Recommendation — proposed, not approved

Use a cursor-derived horizon rather than a hard-coded 30-day or full-year rule:

1. Let C be the last durably reconciled EGX session date (exclusive).
2. Let N be the next session date that the scheduler may evaluate, determined only from explicit calendar records.
3. Require the candidate calendar to cover every date from C + 1 through N, inclusive, with no gaps.
4. Require the candidate to preserve explicit status and session-time records for all dates in that interval. A SCHEDULED or OPEN date is not a completed session.
5. Re-run the same check for rollback targets; a historically active version is not automatically safe for the current cursor.

This rule ties coverage to the work the runtime must perform. It deliberately does not prescribe a fixed forward buffer.

## 4. Bootstrap decision still required

The cursor-derived rule cannot be used for the first activation until the system has a durable cursor. The owner must select one explicit bootstrap policy:

- **Operator-supplied start date:** the operator supplies the first date from which the system must reconcile; the candidate must cover that date through the next scheduled evaluation.
- **Calendar-start bootstrap:** the system begins from the candidate's coverage_start; this may create a large historical reconciliation and requires a separately approved initial backfill limit.
- **No activation until a cursor exists:** activation remains blocked until a controlled bootstrap process writes the first durable cursor.

Do not silently choose a start date from the machine's current date or assume that all prior dates are irrelevant.

## 5. Activation transaction and API prerequisites

Before adding activation endpoints, implement and test:

1. Verify the target version exists and its persisted content hash passes integrity validation.
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
- Initial activation is rejected until the approved bootstrap policy is satisfied.
- Failed activation and rollback preserve the prior active pointer and append no misleading success event.
- Concurrent activation attempts serialize; the final pointer and audit events remain consistent.
- Actor identity comes from the authenticated principal, and non-operators receive 403.
- Activation does not mark provider bars final, does not enable lifecycle monitoring by itself, and does not change Crash Radar scoring.

## 7. Current implementation boundary

- Immutable calendar persistence, content-hash verification, active pointer, and audit-event primitives are implemented.
- Authenticated publication and read endpoints are in PR #462.
- No real EGX calendar version is published or active.
- No durable lifecycle evaluation cursor or scheduler is connected to the calendar.
- Provider finality attestation and per-day source evidence remain open.

**Gate result: do not expose activation/deactivation/rollback over HTTP until the bootstrap and cursor-derived coverage policy are approved and the required persistence/recovery tests pass.**
