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

This domain primitive does not load operator files, persist calendar versions, expose management APIs, schedule jobs, or connect to lifecycle monitoring/Crash Radar. It does not generate a 2026/2027 calendar from national holidays or infer weekends. It does not prove provider daily-bar completion. The runtime integration remains disabled until operator calendar publication, provider completion attestation, and recovery integration tests are complete.

## Operator publication controls still required

1. An authenticated operator workflow to publish an immutable calendar version.
2. Provenance for each closure/schedule override (official EGX notice reference and operator audit identity).
3. Validation that the new version covers the active operational horizon without gaps.
4. Explicit activation and rollback to a prior immutable version.
5. Every evaluation must persist the calendar version and session date used.
