# DEC-081 — M22 Historical Analysis Comparison Design Gate

**Status:** Proposed  
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

## 6. Open Design Questions

Before implementation, the following questions must be explicitly accepted:

1. **Selection contract:** should snapshots be selected by UUID, analysis date, or both?
2. **Same-date snapshots:** if multiple snapshots exist on the same date, should UUID be mandatory for unambiguous selection?
3. **Comparison direction:** should the response define an explicit `before` and `after` snapshot?
4. **Derived fields:** which deltas should be exposed (scores, price, support/resistance), and which should remain as raw before/after values only?
5. **Classification changes:** should a classification change be represented as a boolean/change descriptor or simply as before/after values?
6. **Missing snapshot:** should a missing snapshot return a domain/application not-found result that maps to HTTP 404?
7. **Cross-symbol selection:** should different-stock snapshot IDs be rejected explicitly?
8. **Dashboard presentation:** side-by-side table, change rows, or another presentation?
9. **API shape:** dedicated comparison endpoint versus extending the history endpoint.
10. **No analytical recalculation:** which invariants should prove that comparison is purely read-side?

## 7. Alternatives

### A. Extend the history endpoint

Example: `GET /api/v1/history/{symbol}/compare?before=...&after=...`

**Benefit:** keeps comparison under the historical resource.

**Trade-off:** history retrieval and comparison become more tightly coupled.

### B. Dedicated comparison endpoint

Example: `GET /api/v1/comparisons/{symbol}?before=...&after=...`

**Benefit:** gives comparison its own explicit read-side contract.

**Trade-off:** introduces another resource boundary.

### C. Dashboard-only comparison

**Benefit:** no new backend endpoint.

**Trade-off:** pushes comparison semantics into the presentation layer and makes the behavior difficult to reuse or test independently.

## 8. Proposed Invariants

1. Both selected snapshots belong to the requested stock.
2. The two selected snapshots are distinct.
3. The comparison does not execute fresh analysis.
4. The comparison does not mutate persisted snapshots.
5. Before/after direction is explicit and deterministic.
6. Any derived delta is calculated from persisted values only.
7. Existing history/latest-result/report/alert contracts remain unchanged.
8. Persistence schema is unchanged.

## 9. TDD Acceptance Shape

The accepted implementation should test:

- comparison of two existing snapshots;
- explicit before/after direction;
- same-date snapshots selected by UUID;
- missing snapshot;
- cross-symbol snapshot rejection;
- identical snapshot rejection;
- deterministic derived deltas;
- unchanged persisted values;
- no fresh analysis execution;
- API response contract;
- dashboard comparison presentation;
- existing history/report/alert behavior remains unchanged.

## 10. Design Gate Decision

**Status: Proposed — implementation is not authorized until the open questions are resolved and this gate is accepted.**

## 11. Revisit Conditions

Revisit this gate if the requirement expands into performance analytics, return calculations, predictive analysis, ranking, charting, or portfolio behavior. Those capabilities should receive separate design gates.