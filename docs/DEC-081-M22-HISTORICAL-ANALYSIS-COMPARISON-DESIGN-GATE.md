# DEC-081 — M22 Historical Analysis Comparison Design Gate

**Status:** Accepted  
**Date:** 2026-09-18  
**Milestone:** M22 — Historical Analysis Comparison

---

## 1. Problem

M20 introduced immutable historical analysis snapshots and M21 made those snapshots readable through the API and dashboard.

The current user-facing capability still requires the user to inspect snapshots individually. It does not provide an explicit way to compare two stored snapshots for the same stock and understand what changed between analysis dates.

A comparison capability would be a derived read-side behavior over already-persisted snapshots. It must not become a second analytical engine or recalculate historical analysis.

## 2. Desired Outcome

M22 should define the smallest capability that allows a client to:

1. select two existing historical snapshots for the same stock;
2. inspect their dates and persisted analytical values;
3. identify relevant changes between the snapshots;
4. distinguish persisted values from derived comparison values;
5. preserve the existing history, latest-report, and alert contracts;
6. remain read-only and never trigger fresh analysis.

## 3. In Scope

- comparison of two persisted snapshots for one stock;
- explicit snapshot selection;
- comparison application use case;
- transport read model;
- deterministic comparison semantics;
- handling of missing or invalid snapshot selections;
- API contract;
- dashboard presentation;
- tests;
- explicit separation between persisted values and derived deltas.

## 4. Out of Scope

- recalculating technical or fundamental analysis;
- changing scoring or opportunity-classification rules;
- comparing different stocks;
- historical ranking;
- portfolio performance;
- trade simulation;
- OHLC charting;
- notifications;
- watchlists;
- persistence schema changes;
- AI-generated explanations;
- predictive conclusions.

## 5. Proposed Boundary

    Dashboard
        ↓
      HTTP
        ↓
CompareAnalysisSnapshots
        ↓
AnalysisResultStore
        ↓
Persisted Historical Snapshots

The comparison use case owns only selection validation and deterministic comparison of persisted snapshots. The store remains responsible for retrieving persisted records.

## 6. Accepted Design Decisions

### 1. Selection Contract

Snapshots are selected by UUID. The API requires both `before` and `after` snapshot IDs.

Dates remain part of the returned snapshot data for human-readable context, but dates are not selection identifiers.

This keeps selection unambiguous when multiple snapshots exist on the same analysis date.

### 2. Same-Date Snapshots

Same-date snapshots are valid and are distinguishable by UUID. UUID is therefore the canonical selection key.

The comparison must reject the same UUID supplied for both sides.

### 3. Comparison Direction

The response has explicit `before` and `after` snapshots.

The `before` snapshot is the earlier selected reference conceptually, but the API does not silently reorder caller selections. The client explicitly chooses which snapshot is `before` and which is `after`.

The response preserves the selected dates so a client can see if its direction is chronological.

### 4. Derived Fields

M22 exposes deltas only for numeric values that are already persisted in the analysis result and have a clear direct subtraction meaning:

- technical score;
- fundamental score;
- stock quality score;
- entry quality score;
- current price when present in both snapshots;
- nearest support when present in both snapshots;
- nearest resistance when present in both snapshots.

For optional numeric values, the delta is `null` when either side is missing.

Enum/status fields and fundamental period dates remain before/after values only; no artificial numeric encoding is introduced for them.

### 5. Classification Changes

Opportunity classification is represented as explicit before/after values plus a boolean `changed`.

No ranking, severity, or interpretation is derived from the classification transition.

### 6. Missing Snapshot

A selected snapshot that does not exist returns an application-level not-found result and maps to HTTP 404.

The endpoint does not fall back to latest history or silently choose another snapshot.

### 7. Cross-Symbol Selection

Both snapshots must belong to the requested symbol.

A mismatch is rejected explicitly as an invalid comparison selection and maps to HTTP 400.

### 8. Dashboard Presentation

The dashboard presents the comparison as a before/after view with:

- snapshot date;
- opportunity classification;
- technical score;
- fundamental score;
- stock quality;
- entry quality;
- current price;
- nearest support;
- nearest resistance;
- derived numeric deltas;
- classification-changed indicator.

The dashboard does not calculate deltas itself.

### 9. API Shape

Use a dedicated read-only endpoint:

`GET /api/v1/comparisons/{symbol}?before={uuid}&after={uuid}`

Comparison is its own application resource boundary. This avoids making the history endpoint responsible for two different read behaviors.

### 10. No Analytical Recalculation

The comparison capability receives only persisted `AnalysisResultRecord` values from `AnalysisResultStore.get_history` (or an equivalent store-level snapshot lookup added without changing persistence schema).

It never invokes `RunStockAnalysis`, `DailyMarketAnalysis`, market-data providers, scoring services, or classification services.

Tests must use a store double and prove no analysis execution is triggered.

## 7. Accepted Boundary

```
Dashboard
    ↓
HTTP
    ↓
CompareAnalysisSnapshots
    ↓
AnalysisResultStore
    ↓
Persisted Historical Snapshots
```

The comparison use case owns selection validation and deterministic comparison. The store owns persistence retrieval. The API owns transport mapping. The dashboard owns presentation only.

## 8. TDD Acceptance Criteria

The implementation must test:

- two existing snapshots compare successfully;
- caller-selected before/after direction is preserved;
- same-date snapshots can be selected by UUID;
- identical snapshot IDs are rejected;
- missing snapshot IDs return a not-found application result;
- cross-symbol snapshots are rejected;
- numeric deltas are deterministic;
- optional numeric values produce null deltas when either side is missing;
- classification exposes before/after and changed;
- persisted records are not mutated;
- no fresh analysis is executed;
- API 200/400/404 contracts;
- dashboard renders comparison data without calculating deltas;
- existing history/report/alert contracts remain unchanged.

## 9. Design Gate Decision

**Status: Accepted — implementation is authorized for the M22 MVP defined here.**

The implementation must not introduce persistence schema changes, new analytical rules, ranking, prediction, or cross-stock comparison.

## 10. Revisit Conditions

**Status: Proposed — implementation is not authorized until the open questions are resolved and this gate is accepted.**

## 11. Revisit Conditions

Revisit this gate if the requirement expands into performance analytics, return calculations, predictive analysis, ranking, charting, or portfolio behavior. Those capabilities should receive separate design gates.