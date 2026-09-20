# DEC-112 — M50 Analysis Run History Design Gate

**Status:** Proposed  
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

## 7. Open Questions

These must be resolved before implementation:

1. Snapshot ordering: by analysis date, snapshot ID, or execution/universe order?
2. Run visibility: should authenticated users see only runs produced under their ownership context, with system/global runs remaining operator-visible under the existing ownership rules?
3. Legacy snapshots: should snapshots with no AnalysisRunId be omitted from run views and remain available only through existing stock-history views?
4. Failed symbols: should the read model expose failed symbol identifiers/reasons from the aggregate execution record, or only successful snapshots?
5. Pagination: should M50 return a bounded snapshot list or require pagination from the first API slice?
6. API shape: dedicated /analysis-runs/{run_id} resource versus a nested history/reporting endpoint.
7. Dashboard scope: run detail only, or run list + run detail?
8. Missing run semantics: 404 at HTTP boundary with an application-level not-found result/error, consistent with existing read-side boundaries?

---

## 8. Required Invariants

1. AnalysisRunId remains the authoritative analytical grouping identity.
2. Scheduled workflow execution ID is never used as the analysis-run identity.
3. API/dashboard code does not infer grouping from timestamps or symbols.
4. Legacy snapshots remain readable through existing history behavior.
5. Failed stocks do not acquire fake snapshots.
6. Empty and all-failed runs remain representable.
7. Ownership checks remain at the existing authenticated application boundary.
8. Read operations do not mutate analysis or persistence state.
9. Existing latest-result and stock-history contracts remain unchanged.
10. No analytical scoring or classification logic is introduced into the read model.

---

## 9. TDD Acceptance Shape

- retrieve a completed run by AnalysisRunId;
- retrieve its successful snapshots;
- deterministic snapshot ordering;
- partial run returns successful snapshots without fake failed snapshots;
- all-failed run returns a valid run with zero successful snapshots;
- empty run returns a valid run with zero snapshots;
- unknown run is handled explicitly;
- legacy snapshots remain available through existing stock-history reads;
- ownership boundary is enforced;
- restart preserves the same read result;
- API contract maps the application read model without persistence leakage;
- dashboard consumes the API contract without recomputing grouping.

---

## 10. Design Gate Decision

**Status: Proposed — implementation is not authorized yet.**

The candidate direction is B. The open questions above are intentionally left explicit because they affect the application/API contract and user-visible behavior.

---

## 11. Revisit Conditions

Revisit this gate if:

- analysis-run grouping changes again;
- a different historical execution identity is introduced;
- distributed execution requires a separate read model;
- ownership semantics change;
- the project decides not to expose analysis-run history as a user-facing capability.
