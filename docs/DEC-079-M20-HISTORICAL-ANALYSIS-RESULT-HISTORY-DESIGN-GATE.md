# DEC-079 — M20 Historical Analysis Result History Design Gate

**Status:** Accepted  
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

## 8. Accepted Decisions

1. **Snapshot identity:** each persisted snapshot receives a generated UUID. The UUID identifies the persisted analytical snapshot and is independent of transport/API identity.
2. **Same-day runs:** multiple completed runs for the same symbol and date are allowed. The snapshot UUID makes them distinct.
3. **Current `get(symbol)` semantics:** `get(symbol)` continues to return the latest completed snapshot for compatibility with existing report/alert consumers.
4. **Historical retrieval:** the store gains an explicit history query by symbol with optional date bounds and deterministic newest-first ordering. History retrieval never executes analysis.
5. **Latest result source:** the latest result is derived from the history records rather than maintained as a second analytical source of truth.
6. **SQLite migration:** the existing latest-only row is migrated into the history representation as one snapshot. Existing completed state is preserved; no historical records are fabricated for periods that were not stored.
7. **Serialization failures:** corrupt or unsupported historical payloads remain explicit persistence errors. Reads do not silently skip or repair corrupt records.
8. **Failed analysis:** failed executions do not create successful historical snapshots. A snapshot is appended only after the single-stock analysis completes successfully and its result is available.
9. **Ordering semantics:** snapshots are ordered by analysis date descending, then snapshot UUID ascending as a deterministic tie-breaker. The date remains the business analysis period; the UUID is not interpreted as time.
10. **API exposure:** M20 is application/infrastructure scope only. Historical HTTP/dashboard exposure requires a separate design gate.

### Storage Shape

The SQLite MVP will use a dedicated history table keyed by snapshot UUID. The existing latest-only table is migrated into it, after which `get(symbol)` queries the newest historical snapshot.

Historical records are append-only. Existing report/alert reads remain on the `get(symbol)` compatibility path.

### Compatibility

The application-facing `AnalysisResultStore` contract retains `save`, `get`, and `get_record`; M20 adds an explicit history query without exposing SQLite types to application/domain code.

---

## 9. Invariants

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

## 10. TDD Acceptance Criteria

The implementation should establish behavior for:

- saving multiple snapshots for one symbol;
- retrieving snapshots in deterministic newest-first order;
- preserving snapshots across store recreation;
- latest-result compatibility;
- multiple runs on the same date;
- failed analysis not creating a historical snapshot;
- corrupt/unsupported historical payload handling;
- migration of an existing latest-only row;
- no recalculation during historical reads;
- deterministic date-bound history queries;
- generated snapshot identity uniqueness.

API exposure, if needed, must be designed separately rather than added implicitly.

---

## 11. Design Gate Decision

**Status: Accepted — implementation is authorized for the M20 MVP defined here.**

The implementation must preserve the existing latest-result behavior while adding append-only historical snapshots behind `AnalysisResultStore`. No API/dashboard work is authorized by this gate.

---

## 12. Revisit Conditions

Revisit this gate if:

- the product requirement changes from historical result snapshots to historical market-data reconstruction;
- strategy versioning becomes a required business concept;
- historical analytics require a different persistence model;
- the existing latest-result API contract cannot be preserved without unacceptable complexity.
