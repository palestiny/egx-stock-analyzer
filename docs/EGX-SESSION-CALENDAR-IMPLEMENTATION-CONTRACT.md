# Versioned EGX Session Calendar — Implementation Contract

## Authority and purpose

DEC-139 requires a versioned, operator-maintained EGX session calendar until an authoritative machine-readable EGX source is verified. This calendar is the only source of trading-day and session-close semantics for lifecycle evaluation. Weekday-only inference is prohibited.

The calendar timezone is `Africa/Cairo`. Every date inside the declared coverage range must have exactly one explicit record. This includes non-trading days; an omitted date is a coverage defect, not an implicit weekend or holiday.

## Day records

| Status | Meaning | Eligible as a completed session? |
|---|---|---|
| `NON_TRADING` | Explicitly confirmed no EGX session | No |
| `SCHEDULED` | Trading session planned, not yet opened | No |
| `OPEN` | Session is in progress | No |
| `CLOSED` | Session explicitly confirmed closed, with timezone-aware `closed_at` | Yes, only after `closed_at` |
| `CANCELLED` | Planned session cancelled | No |

Each trading session has explicit open and close times. This supports Ramadan and exceptional shortened sessions without global time assumptions. `CLOSED` requires an explicit timezone-aware confirmation timestamp. No session is considered complete merely because its scheduled close time has passed.

## Versioned JSON shape

```json
{
  "version": "egx-2026-11-v1",
  "timezone": "Africa/Cairo",
  "coverage_start": "2026-11-01",
  "coverage_end": "2026-11-03",
  "days": [
    {"date": "2026-11-01", "status": "SCHEDULED", "session_open": "10:00", "session_close": "14:30"},
    {"date": "2026-11-02", "status": "NON_TRADING", "reason": "Operator-confirmed closure"},
    {"date": "2026-11-03", "status": "CLOSED", "session_open": "10:00", "session_close": "14:30", "closed_at": "2026-11-03T15:30:00+02:00"}
  ]
}
```

The sample is a schema illustration only, not an asserted historical EGX schedule.

## Safety invariants implemented

- Version and IANA timezone are mandatory; the timezone must be `Africa/Cairo`.
- Coverage is contiguous and explicit: one ordered record per calendar date.
- Missing dates and out-of-range requests fail closed.
- Trading records require explicit open and close times; close must follow open.
- `CLOSED` requires a timezone-aware `closed_at`; the confirmation cannot be treated as effective before that instant.
- Non-trading and cancelled dates cannot carry trading-session times.
- Queries return only explicitly `CLOSED` sessions. `SCHEDULED` and `OPEN` sessions remain separately queryable as unconfirmed.

## Deliberately not implemented yet

This domain primitive and persistence adapter do not load operator files, schedule jobs, or connect to lifecycle monitoring/Crash Radar. The authenticated operator API supports manual publication and read operations only. The persistence adapter stores immutable, SHA-256-verified calendar versions and append-only activation/deactivation/rollback audit events, but no real EGX calendar has been published or activated. The system does not generate a 2026/2027 calendar from national holidays or infer weekends, and it does not prove provider daily-bar completion. Runtime integration remains disabled until an operator-verified calendar can be safely activated under an explicit coverage policy, provider completion attestation is available, and recovery integration tests pass.

## Operator API surface

The authenticated operator API currently supports:

- `POST /api/v1/owner/session-calendars/versions` to publish a validated immutable version.
- `GET /api/v1/owner/session-calendars/versions` to list version metadata.
- `GET /api/v1/owner/session-calendars/versions/{version}` to read a full version.
- `GET /api/v1/owner/session-calendars/active` to inspect the active version (404 when none is active).
- `GET /api/v1/owner/session-calendars/activation-events` to inspect the append-only activation audit.

Every route requires operator authorization. The publication actor is taken from the authenticated identity; clients cannot submit or override `published_by`. Publication stores a calendar-level source reference and reason. Per-day evidence references are not yet modeled.

**Audit identity limitation:** the current legacy operator credential resolves to the shared subject `operator` (and the shared legacy operator user ID). Therefore the audit record distinguishes the legacy operator credential class from ordinary users, but it does not identify which human used a shared token. The API rejects blank subjects and never trusts a body-supplied actor, but this is not individual accountability. Before real operational publication, the owner must approve named operator accounts/credentials with an explicit operator permission, or an alternative auditable human-identity mechanism. Do not represent the current shared subject as a unique person.

Activation, deactivation, and rollback are deliberately not exposed through HTTP yet. The operational coverage horizon has not been defined, so there is no safe activation precondition to enforce. Publishing a version does not make it active, and no calendar is currently activated by this implementation.

## Operator controls still required

1. Capture verifiable source provenance for each exceptional closure/session override, not only a calendar-level reference.
2. Define and validate the active operational horizon; the policy is not yet defined.
3. Add authenticated activation/deactivation/rollback endpoints only after coverage validation is enforceable.
4. Every evaluation must persist the calendar version and session date used.

The activation coverage-horizon options and unresolved initial-cursor/bootstrap decision are documented in `docs/EGX-SESSION-CALENDAR-ACTIVATION-DESIGN-GATE.md`.
