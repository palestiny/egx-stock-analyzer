# DEC-113 — M51 Analysis Run History Query Design Gate

**Status:** Proposed  
**Date:** 2026-09-20  
**Milestone:** M51 — Analysis Run History Query

## Context

M50 established a read-only detail capability for one AnalysisRunId and its successful correlated snapshots.

M50 intentionally deferred a run-level list/search/filter surface. The current dashboard can inspect a known run, but there is no application capability for discovering which analysis runs exist.

This is a read-side query problem, not a change to analysis execution or snapshot persistence.

## Desired Outcome

Introduce an application read capability that can:

1. list persisted analysis runs;
2. order them deterministically;
3. apply bounded pagination;
4. optionally filter by aggregate execution state;
5. expose enough metadata to select a run for M50 detail;
6. keep query semantics in the application layer;
7. reuse the existing durable AnalysisRunStore boundary.

## Scope

### In Scope

- analysis-run list/read contract;
- deterministic ordering;
- bounded pagination;
- optional aggregate-state filtering;
- authenticated read boundary;
- explicit empty-result behavior;
- API contract;
- dashboard discovery surface only if the API contract is accepted;
- restart consistency.

### Explicitly Out of Scope

- changing analysis execution;
- changing AnalysisRun persistence semantics;
- changing snapshot correlation;
- editing/deleting runs;
- stock-level analytical calculations;
- ranking opportunities;
- trading decisions;
- scheduled-workflow lifecycle changes;
- distributed querying;
- user ownership changes;
- full-text search.

## Alternatives

### A — Query AnalysisRunStore Directly from API

**Advantage:** minimal application code.

**Trade-off:** leaks persistence/query semantics into transport and makes future filtering/pagination harder to evolve consistently.

**Assessment:** Not selected.

### B — Dedicated ListAnalysisRuns Application Read Capability

**Advantage:** explicit query ownership, reusable by API/dashboard, preserved persistence boundaries, and independent testability.

**Trade-off:** adds one application read capability and a read model.

**Assessment:** Preferred candidate.

### C — Reconstruct Runs from Snapshot History

**Advantage:** could reuse existing snapshot queries.

**Trade-off:** cannot reliably represent empty/all-failed runs, duplicates run metadata/query semantics, and weakens AnalysisRunStore as the run authority.

**Assessment:** Not selected.

## Open Questions

These must be resolved before implementation:

1. **Ordering:** runs by created_at DESC with AnalysisRunId as deterministic tie-breaker?
2. **Pagination:** same opaque cursor approach as M50 rather than offset pagination?
3. **State filter:** all persisted aggregate states or terminal states only?
4. **Page size:** reuse existing 50 default / 100 maximum bounds?
5. **Metadata:** which run fields are necessary for discovery without duplicating snapshot detail?
6. **Empty result:** normal empty collection rather than 404?
7. **Dashboard:** include discovery in the first slice, or validate API/application behavior first?
8. **Ownership:** continue M50's authenticated system-level visibility boundary until a dedicated ownership gate changes it?

## Proposed Invariants

1. AnalysisRunId remains the authoritative run identity.
2. Scheduled workflow execution IDs are never substituted for analysis-run IDs.
3. Query ordering is deterministic and independent of database incidental order.
4. Pagination is bounded and opaque to transport consumers.
5. Filtering does not mutate persisted runs.
6. Empty results are not treated as an application error.
7. API/dashboard code does not query SQLite directly.
8. M50 single-run detail behavior remains unchanged.
9. No analytical scoring or classification logic is introduced.
10. Restart returns the same persisted query result for unchanged data.

## TDD Acceptance Shape

- list multiple runs in deterministic order;
- apply accepted state-filter semantics;
- return bounded pages;
- continue using an opaque cursor;
- reject malformed/foreign cursors as controlled client errors;
- return an empty collection when no runs match;
- preserve M50 detail behavior;
- enforce the existing authenticated visibility boundary;
- verify restart consistency against durable SQLite data;
- map the application read model to HTTP without persistence leakage.

## Design Gate Status

**Proposed — implementation is not authorized yet.**

The next action is to resolve the open questions above and record the accepted M51 contract before implementation.
