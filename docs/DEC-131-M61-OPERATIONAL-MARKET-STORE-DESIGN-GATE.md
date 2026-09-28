# DEC-131 — M61 Operational Market Store & Incremental Acquisition Design Gate

**Status:** Proposed  
**Date:** 2026-09-28  
**Milestone:** M61 — Backtesting & Strategy Validation

## Purpose

DEC-128/129/130 established the immutable historical-dataset evidence boundary for reproducible backtesting. This gate defines the separate operational market-data boundary required for daily analysis and incremental acquisition.

The operational store must not replace the immutable M61 evaluation dataset.

## Problem

Repeatedly requesting an entire historical range from an external provider is inefficient, obscures provenance, increases provider dependency, and can introduce avoidable source drift.

The system needs to retain acquired market observations locally and request only missing market sessions. Current-session observations also have different mutability semantics from finalized historical observations.

## Architectural Boundary

```
External Provider
      ↓
Acquisition Boundary
      ↓
Validation / Provenance
      ↓
Operational Market Store
      ↓
Analysis Input
```

The provider is an acquisition source, not the permanent source of historical analysis.

The immutable M61 historical dataset remains a separate evidence boundary:

```
Immutable M61 Dataset → Backtest / Historical Evaluation
Operational Market Store → Daily / Current Analysis
```

## Decisions

### D1 — Canonical Observation Identity

A market observation is uniquely identified by:

```
(stock_id, timeframe, timestamp)
```

A repeated observation with the same identity must not create a duplicate row.

### D2 — Incremental Acquisition

Before acquisition, the application evaluates local coverage and determines missing expected trading sessions.

Only missing ranges are requested from the provider.

The acquisition layer must not re-download the complete historical range when local coverage already satisfies the requested range.

### D3 — Trading-Session Awareness

Calendar days are not automatically expected market observations.

Gap detection must operate through an explicit expected-session boundary. Weekends, exchange holidays, and other non-trading dates must not be reported as missing market observations merely because no row exists.

A complete EGX trading calendar is a follow-up boundary; the operational store must not hard-code weekday-only assumptions as authoritative market-calendar logic.

### D4 — Idempotent Duplicate Handling

If an incoming observation has an existing identity:

- identical validated values → no-op;
- different values → explicit data conflict;
- silent overwrite → prohibited.

### D5 — Conflict Handling

A conflicting observation must produce a durable quality/provenance event containing enough information to identify:

- observation identity;
- existing values/source;
- incoming values/source;
- acquisition identity;
- detection time.

Conflict resolution is a separate policy and must not be hidden inside persistence.

### D6 — Acquisition Provenance

Every acquisition operation receives an acquisition identity and records provider, source symbol, requested range, actual returned range, timing, status, row count, and raw-artifact integrity metadata where preservation is permitted.

Observation rows may reference the acquisition that introduced them.

### D7 — Current Session Lifecycle

Current-session data is provisional and may change.

The minimum session lifecycle is:

```
EXPECTED → OPEN → CLOSED → FINALIZED
```

Analysis that requires finalized historical data must use FINALIZED observations.

Current-session analysis may explicitly opt into provisional observations.

### D8 — Raw vs Derived Data

Raw provider observations and adjusted/derived analytical series are separate concepts.

No provider-specific adjustment is silently applied to the canonical raw operational observation.

### D9 — Operational Store vs Immutable Dataset

The operational store is mutable and incrementally maintained.

An accepted M61 dataset version is immutable. Operational-store updates must never mutate or invalidate an accepted backtest dataset version.

### D10 — First Implementation Slice

Implementation starts with COMI only.

The vertical slice must prove acquisition, persistence, coverage, gap detection, idempotency, conflict handling, and analysis-input retrieval before expansion to the remaining nine-symbol cohort.

## Proposed Core Contracts

### MarketObservation

The canonical operational record contains:

- stock_id
- timeframe
- timestamp
- open
- high
- low
- close
- volume
- source
- acquisition_id

The identity is `(stock_id, timeframe, timestamp)`.

### AcquisitionRecord

Minimum fields:

- acquisition_id
- provider
- source_symbol
- stock_id
- requested_from
- requested_to
- actual_from
- actual_to
- requested_at
- completed_at
- status
- row_count
- raw_artifact_hash

### MarketSession

Minimum lifecycle fields:

- session_date
- market
- status
- opened_at
- closed_at

### Quality/Conflict Event

Minimum fields:

- event_id
- observation identity
- event_type
- detected_at
- acquisition_id
- existing/incoming provenance
- structured details

## Acceptance Tests

The COMI vertical slice is accepted only when all are demonstrated:

1. Empty store + bounded acquisition persists validated observations.
2. Repeating the same request does not call the provider for already-covered sessions.
3. Extending the requested range acquires only the missing expected sessions.
4. Weekend/non-session dates are not treated as gaps.
5. Identical duplicate observations are idempotent.
6. Conflicting observations are recorded as explicit conflicts and are not silently overwritten.
7. Acquisition provenance is queryable.
8. Current-session observations can be updated without weakening finalized-history semantics.
9. Finalized observations are available to historical analysis without provider access.
10. A provider outage after local coverage is sufficient does not prevent analysis.
11. The operational store does not mutate the immutable M61 dataset.
12. The same local state produces deterministic analysis input.

## Non-Goals

This gate does not decide:

- final production market-data provider;
- PostgreSQL vs SQLite as the permanent operational database;
- automatic provider fallback;
- intraday streaming architecture;
- order execution;
- portfolio management;
- corporate-action adjustment methodology;
- full EGX historical universe reconstruction.

## Trade-offs

### Re-download full history vs incremental acquisition

Incremental acquisition reduces network/provider dependency and makes local history the stable analysis input, at the cost of maintaining coverage and session semantics.

### Mutable operational store vs immutable dataset

Keeping them separate allows daily analysis to evolve while preserving reproducible backtest evidence.

### Conflict overwrite vs explicit conflict

Explicit conflicts are more operationally demanding but prevent silent corruption and preserve provenance.

### Database-first vs contract-first

The domain/application contracts are fixed before selecting the permanent storage engine. This avoids coupling M61 semantics to a premature infrastructure choice.

## Exit Criteria

DEC-131 can move from Proposed to Accepted after:

1. the contracts above are represented in tests;
2. COMI RED tests exist;
3. a minimal implementation makes those tests GREEN;
4. persistence and acquisition provenance are verified;
5. no accepted M61 dataset semantics are changed.

## Next Implementation Step

Create the COMI RED test slice against an in-memory/fake operational store and provider, then implement the smallest persistence/application boundary required to make the tests GREEN.