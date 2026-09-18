# DEC-079 — M20 Historical Analysis Result History Design Gate

**Status:** Proposed  
**Date:** 2026-09-18  
**Milestone:** M20 — Historical Analysis Result History

---

## 1. Problem

M19 can execute the configured EGX universe repeatedly, but the current `AnalysisResultStore` is intentionally latest-result-only.

That creates a capability gap:

- recurring analysis replaces the previous result for each symbol;
- the system cannot answer what changed between analysis runs;
- historical report comparison is not possible from persisted analysis results;
- recurring execution produces repeated snapshots without retaining the analytical history needed to evaluate them.

The project blueprint explicitly identifies historical observations, historical signals, strategy evaluation, and historical comparisons as long-term requirements.

M20 defines the smallest explicit boundary needed to preserve completed analysis snapshots without changing the analytical rules.

---

## 2. Desired Outcome

M20 should allow the system to:

1. persist more than one completed analysis result for a stock;
2. identify each result by stock and analysis date/execution context;
3. preserve existing latest-result behavior for current report/alert consumers;
4. retrieve historical results deterministically;
5. keep historical storage behind the existing `AnalysisResultStore` abstraction;
6. avoid changing scoring, classification, or market-analysis behavior.

---

## 3. In Scope

- historical result storage contract;
- immutable analysis-result snapshot identity;
- retrieval by symbol and date/range;
- deterministic ordering;
- coexistence of latest and historical reads;
- persistence behavior across process restart;
- migration from the current latest-only SQLite representation;
- application-level tests;
- infrastructure persistence tests.

---

## 4. Out of Scope

- historical market OHLC storage;
- historical ranking;
- charting;
- performance analytics;
- strategy backtesting changes;
- change-detection rules;
- notifications;
- watchlists;
- portfolio management;
- trading;
- AI analysis;
- distributed storage;
- cloud database migration;
- changing the analytical result itself.

---

## 5. Architectural Boundary

Proposed boundary:

```
Analysis / Scheduled Execution
          ↓
AnalysisResultStore
          ↓
Historical Analysis Result Repository
          ↓
SQLite
```

The application layer decides when a completed analysis result should be saved.

The persistence layer owns representation, indexing, migration, and retrieval mechanics.

The domain analysis pipeline remains unaware of SQLite and historical storage mechanics.

---

## 6. Core Design Principle

A historical record is a **snapshot of an already-computed analytical result**.

M20 must not recompute an old result when reading history.

Historical reads are projections of persisted snapshots, just as the current report/alert capabilities are projections of stored results.

---

## 7. Alternatives

### A. Replace latest-only store with history-aware store

One store supports both current and historical reads.

**Benefit:** one persistence boundary and one source of truth.

**Trade-off:** the existing simple `get(symbol)` contract becomes more important to preserve carefully.

### B. Add a separate historical repository

Keep the current store untouched and add another repository specifically for history.

**Benefit:** minimal impact on the current read contract.

**Trade-off:** two persistence boundaries can drift and duplicate storage semantics.

### C. Persist raw market data and reconstruct analysis history

Store market observations and recompute historical analysis when requested.

**Benefit:** potentially richer historical analysis later.

**Trade-off:** historical results could change when analytical rules change; substantially larger scope; mixes historical data acquisition with result-history needs.

**M20 direction:** A is the preferred candidate because the immediate requirement is historical analytical snapshots, not historical market-data reconstruction.

---

## 8. Open Questions

Before implementation, resolve:

1. Snapshot identity: analysis date alone, or date plus execution ID?
2. Can multiple completed runs for the same symbol and date coexist?
3. What does `get(symbol)` return after history is introduced?
4. What is the exact historical retrieval contract?
5. Should the latest result be a query over history or a separately maintained current record?
6. How should existing SQLite rows migrate into the history model?
7. What happens when a historical payload is corrupt or has an unsupported serialization version?
8. Should failed analyses ever create historical records?
9. What date/time semantics are authoritative for historical ordering?
10. How much history does the MVP expose to the API, if any?

---

## 9. Proposed Invariants

1. A successfully completed analysis may produce one historical snapshot.
2. Failed analysis must not create a successful analytical snapshot.
3. Historical snapshots are immutable after persistence.
4. Existing `get(symbol)` semantics remain compatible unless a separate design explicitly changes the API contract.
5. Historical reads never execute fresh analysis.
6. Historical storage remains behind `AnalysisResultStore`.
7. Serialization remains versioned and explicit; pickle remains prohibited.
8. Historical ordering is deterministic.
9. Persistence technology remains an infrastructure concern.
10. M20 does not change analytical scoring or classification.

---

## 10. TDD Acceptance Shape

The implementation should establish behavior for:

- saving multiple snapshots for one symbol;
- retrieving snapshots in deterministic order;
- preserving snapshots across store recreation;
- latest-result compatibility;
- multiple runs on the same date;
- failed analysis not creating a historical snapshot;
- corrupt/unsupported historical payload handling;
- migration of existing latest-only rows;
- no recalculation during historical reads.

API exposure, if needed, must be designed separately rather than added implicitly.

---

## 11. Design Gate Decision

**Status: Proposed — implementation is not authorized yet.**

The next step is to resolve the open questions and record the accepted historical-result contract before implementation.

---

## 12. Revisit Conditions

Revisit this gate if:

- the product requirement changes from historical result snapshots to historical market-data reconstruction;
- strategy versioning becomes a required business concept;
- historical analytics require a different persistence model;
- the existing latest-result API contract cannot be preserved without unacceptable complexity.
