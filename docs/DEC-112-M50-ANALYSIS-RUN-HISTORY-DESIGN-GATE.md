# DEC-112 — M50 Analysis Run History Design Gate

**Status:** Accepted  
**Date:** 2026-09-20  
**Milestone:** M50 — Analysis Run History & Read Model

---

## 1. Context

M49 established a durable AnalysisRunId for market-wide analysis invocations and correlated successful historical stock snapshots with that identity.

The current system can therefore persist:

    Analysis Run
        ├── Snapshot A
        ├── Snapshot B
        └── Snapshot C

but M49 intentionally did not expose an API or dashboard read model for that grouping.

The next capability is to let an authenticated operator inspect one analysis run as a first-class read-side object without leaking SQLite details into the API or dashboard.

---

## 2. Problem Statement

Current historical views answer stock-centric questions such as:

> “What snapshots exist for this symbol?”

M49 makes a new question answerable:

> “What happened in one market-wide analysis run, and which successful stock snapshots belong to it?”

The read-side capability must preserve:

- latest-result compatibility;
- existing stock history behavior;
- M49 correlation semantics;
- scheduled-workflow versus analysis-run identity separation;
- existing authentication and ownership boundaries;
- provider-neutral application architecture.

It must also make partial, all-failed, and empty analysis runs visible without inventing snapshots for failed stocks.

---

## 3. Desired Outcome

Introduce a read-only application capability that can retrieve an analysis run by AnalysisRunId and expose:

- run identity;
- run creation timestamp;
- aggregate execution state;
- the successful snapshot references belonging to the run;
- enough stock identity to render a useful read model;
- deterministic ordering;
- explicit behavior for missing runs and legacy snapshots.

API/dashboard exposure should consume this application read model rather than reconstructing grouping from raw snapshot storage.

---

## 4. Scope

### In Scope

- analysis-run read contract;
- lookup by AnalysisRunId;
- correlation to successful snapshots;
- deterministic snapshot ordering;
- authenticated ownership/visibility boundary;
- behavior for empty, partial, and failed runs;
- legacy snapshot behavior;
- application/API contract tests;
- first dashboard presentation only if the API contract is explicitly accepted.

### Out of Scope

- changing analysis execution;
- changing snapshot persistence semantics;
- new analytical calculations;
- ranking;
- trading decisions;
- notifications;
- scheduled-workflow lifecycle changes;
- modifying legacy snapshots;
- editing or deleting analysis runs;
- distributed execution.

---

## 5. Alternatives

### A — Compose the Read Model from Existing Snapshot Queries

Find snapshots by correlation ID and reconstruct the run in the application layer.

**Advantage**
- minimal new persistence surface.

**Trade-off**
- run metadata and snapshot membership are split across stores;
- empty/all-failed runs require a separate run lookup;
- future run-level queries may repeatedly duplicate composition logic.

### B — Dedicated Analysis Run Read Capability over Existing Run + Snapshot Stores

Introduce an application query capability that reads the durable analysis-run record and the existing snapshot correlation data, then composes one immutable read model.

**Advantage**
- preserves current persistence ownership;
- keeps correlation logic in the application layer;
- provides one stable read contract for future API/dashboard consumers;
- does not require a second analytical persistence model.

**Trade-off**
- adds an application query object and explicit read DTO/model;
- may require a small snapshot query extension for efficient correlation.

### C — Expose Persistence Rows Directly Through the API

Let the API query the run and snapshot tables directly.

**Advantage**
- shortest implementation.

**Trade-off**
- leaks SQLite/schema details into transport;
- duplicates application semantics;
- weakens the existing architecture boundary.

---

## 6. Candidate Direction

**Candidate:** B — dedicated application read capability over the existing run and snapshot stores.

The intended boundary is:

    API / Dashboard
          ↓
    GetAnalysisRun
          ↓
    AnalysisRunStore + AnalysisResultStore
          ↓
    SQLite persistence

The API and dashboard must not infer run membership themselves.

---

## 7. Accepted Contract Decisions

### 1. Snapshot Ordering

Snapshots are ordered by normalized stock symbol ascending, then snapshot ID ascending as a tie-breaker.

M49 did not persist the market-universe execution order, so M50 must not reconstruct it from incidental insertion order or timestamps. Symbol ordering gives the read model a stable, provider-neutral presentation order.

### 2. Run Visibility

M50 does not add a new ownership field to AnalysisRun.

M49 created analysis runs as system-level analytical records without user ownership metadata. Therefore M50 applies the existing authenticated application boundary to analysis-run reads without inventing user ownership semantics that the stored run cannot support. Authenticated callers may read analysis runs available through the existing analysis read boundary; the legacy/operator compatibility path remains subject to its existing rules.

Per-user analysis-run ownership is explicitly deferred to a future identity/ownership design gate rather than being inferred from scheduled-workflow ownership.

### 3. Legacy Snapshots

Snapshots whose analysis_run_id is null are omitted from M50 run detail.

They remain fully available through the existing stock-history capability. M50 does not synthesize run membership for historical data created before M49.

### 4. Failed Symbols

M50 does not expose failed-symbol identifiers or failure reasons because M49 does not persist those details in AnalysisRun. The run-level aggregate state remains authoritative for distinguishing COMPLETED, COMPLETED_WITH_ERRORS, FAILED, and empty runs.

Successful snapshots are exposed separately. A failed symbol never receives a synthetic snapshot.

Adding durable per-symbol failure details would change the M49 persistence contract and is deferred to a separate design gate if operational visibility requires it.

### 5. Pagination

Snapshot results are bounded from the first API slice.

The default page size is 50 and the maximum is 100, matching the established read-side pagination bounds used elsewhere in the project. Pagination applies only to the successful snapshot collection; run metadata and aggregate state remain in the run-level response.

The continuation cursor is opaque and bound to the run ID and effective page size. M50 introduces no filtering beyond the fixed symbol ordering.

### 6. API Shape

M50 exposes a dedicated resource:

GET /api/v1/analysis-runs/{run_id}

The endpoint maps one application read model to transport DTOs. It does not expose persistence rows or SQLite-specific fields.

### 7. Dashboard Scope

M50 adds run detail presentation only.

The dashboard consumes the dedicated analysis-run endpoint and presents run metadata, aggregate state, failed symbols, and the paginated successful snapshot collection. A run list/search/filter surface is deferred because it requires a separate query contract and pagination semantics across runs.

### 8. Missing Run Semantics

The application capability raises an explicit analysis-run-not-found condition when the run ID does not exist.

The HTTP boundary maps that condition to 404, consistent with the existing read-side not-found behavior.

---

## 8. Required Invariants

1. AnalysisRunId remains the authoritative analytical grouping identity.
2. Scheduled workflow execution ID is never used as the analysis-run identity.
3. API/dashboard code does not infer grouping from timestamps or symbols.
4. Legacy snapshots remain readable through existing history behavior.
5. Failed stocks do not acquire fake snapshots.
6. Empty and all-failed runs remain representable.
7. M50 does not invent analysis-run ownership that M49 did not persist.
8. Read operations do not mutate analysis or persistence state.
9. Existing latest-result and stock-history contracts remain unchanged.
10. No analytical scoring or classification logic is introduced into the read model.
11. Snapshot ordering is deterministic and independent of persistence insertion order.
12. Snapshot pagination is bounded and applied to successful correlated snapshots only.

---

## 9. TDD Acceptance Shape

- retrieve a completed run by AnalysisRunId;
- retrieve its successful snapshots in deterministic symbol order;
- pagination returns bounded pages with an opaque continuation cursor;
- partial run returns successful snapshots without fake snapshots;
- all-failed run returns a valid run with zero successful snapshots and FAILED aggregate state;
- empty run returns a valid run with zero snapshots and no failed symbols;
- unknown run is handled explicitly and maps to HTTP 404;
- legacy snapshots remain available through existing stock-history reads;
- authenticated read boundary follows the existing analysis visibility rules without adding synthetic ownership;
- restart preserves the same read result;
- API contract maps the application read model without persistence leakage;
- dashboard consumes the API contract without recomputing grouping or analytical values.

---

## 10. Design Gate Decision

**Status: Accepted — implementation is authorized for the M50 MVP defined here.**

The selected direction is B — dedicated application read capability over the existing AnalysisRunStore and AnalysisResultStore.

The intended boundary is:

```
API / Dashboard
      ↓
GetAnalysisRun
      ↓
AnalysisRunStore + AnalysisResultStore
      ↓
SQLite persistence
```

M50 is a read-side capability only. It does not change analysis execution, snapshot persistence semantics, authentication, scheduled-workflow lifecycle, ranking, notifications, or analytical logic.

## 11. Revisit Conditions

Revisit this gate if:

- analysis-run grouping changes again;
- a different historical execution identity is introduced;
- distributed execution requires a separate read model;
- ownership semantics change;
- the project decides not to expose analysis-run history as a user-facing capability.
