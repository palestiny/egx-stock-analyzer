# Crash Radar — Configured Universe Contract

## Purpose

This increment implements the DEC-135 operator-configurable, versioned monitored-universe boundary for the existing Market Breadth & Stress Pulse endpoint. It does not change the 50/40/10 heuristic, create alerts, or claim complete EGX coverage.

## Operator configuration

Set both environment variables:

- `EGX_CRASH_RADAR_SYMBOLS`: comma-separated symbols, normalized to uppercase and rejected if duplicates are present.
- `EGX_CRASH_RADAR_UNIVERSE_VERSION`: operator-maintained immutable identifier for that exact symbol set.

Example:

```dotenv
EGX_CRASH_RADAR_SYMBOLS=COMI,EGAL,SWDY,ETEL
EGX_CRASH_RADAR_UNIVERSE_VERSION=egx-universe-2026-11-v1
```

The application rejects partial configuration: symbols and version must be supplied together. A new symbol set must receive a new version identifier. This is deployment/operator configuration in this increment; it is not yet an interactive universe-management screen or a persisted revision history.

## API behavior

`GET /api/v1/market-intelligence/breadth-stress`

- Without `symbols`, use the configured universe and return `universe.source=OPERATOR_CONFIGURED`, its version, and the exact ordered symbol list.
- With `symbols`, evaluate that caller-supplied subset and return `universe.source=CALLER_SUPPLIED`, `version=null`, and the exact normalized symbols.
- If neither source supplies symbols, preserve the existing 400 validation response.

The universe metadata makes the score denominator and configured revision traceable. It does not imply that the universe is complete or that every symbol has a current analysis.

## Explicit limitations

- The score formula and its denominator remain unchanged.
- Caller-supplied universes are custom/partial and must not be described as the full EGX.
- Calendar-day snapshot ages remain evidence metadata, not a completed-session freshness verdict.
- The official EGX session/holiday calendar, one-completed-session freshness evaluation, minimum-coverage behavior, score suppression, and durable score-history/correction ledger remain separate open work.
- No Crash Radar notifications are enabled.


## Completed-session freshness — 2026-11-13

The breadth/stress response now exposes per-symbol `source_data_freshness_by_symbol`
and aggregate `source_data_freshness_status`, using the source-bar timestamp
converted to the Cairo session date and the active persisted session-calendar
version.

- `STALE`: at least one later EGX session is explicitly marked CLOSED and its
  `closed_at` instant is no later than the evaluation cutoff.
- `FRESH`: no later completed session exists, and the covered interval contains
  no unconfirmed SCHEDULED/OPEN trading session.
- `UNKNOWN`: no timestamp, no active calendar, a calendar coverage gap, or an
  unconfirmed trading session prevents a reliable verdict.
- `FUTURE`: the source timestamp/date is later than the evaluation cutoff. It is
  also listed among `unknown_source_data_freshness_symbols` so it cannot be
  mistaken for fresh evidence.

The aggregate is `UNKNOWN` when no symbol has a known FRESH/STALE verdict,
`PARTIAL` when known results coexist with missing/unknown/future evidence,
`STALE` when at least one symbol is stale and none are unknown, and `FRESH`
only when all requested symbols have a known fresh verdict.

This is evidence metadata only. It does not alter the 50/40/10 score, introduce a
minimum-coverage threshold, suppress the legacy score, create alerts, or claim
that the active calendar has independently verified source authenticity. The
calendar activation/authenticity gate remains separate; no calendar was activated
as part of this implementation. With no active calendar, freshness correctly
remains UNKNOWN.
