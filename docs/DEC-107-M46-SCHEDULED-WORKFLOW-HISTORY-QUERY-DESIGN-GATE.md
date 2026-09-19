# DEC-107 — M46 Scheduled Workflow History Query Extensions Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M46

## 1. Problem

M45 makes the complete persisted lifecycle history of one scheduled workflow execution visible through a read-only application/API/dashboard boundary.

M45 intentionally defers pagination and query extensions. Returning the complete history is appropriate for the current bounded MVP, but lifecycle history can grow as executions become longer-lived or acquire additional transitions.

M46 should decide whether and how the history read boundary should support bounded retrieval without changing lifecycle persistence or mutation semantics.

## 2. Desired Outcome

An authorized caller should be able to retrieve a bounded portion of one execution's lifecycle history while preserving the authoritative persisted sequence.

The capability must remain read-only and must not introduce alternate history ordering, history reconstruction, lifecycle mutation, or a second persistence source.

## 3. Proposed Boundary

```
HTTP / Dashboard
       ↓
GetScheduledWorkflowExecutionHistory
       ↓
ScheduledWorkflowExecutionStore
       ↓
SQLite lifecycle history
```

M46 should extend the existing read-side capability rather than introduce a parallel history query path.

## 4. In Scope

- bounded history retrieval for one execution;
- explicit query parameters and validation;
- stable sequence-based pagination semantics;
- preservation of existing ownership authorization;
- deterministic response metadata;
- application/API contract tests;
- dashboard presentation only if explicitly accepted.

## 5. Out of Scope

- changing lifecycle transitions;
- changing the persisted history schema unless the accepted design proves it necessary;
- history deletion or retention policy;
- event replay;
- event sourcing;
- cross-execution analytics;
- aggregation across users;
- new authentication or authorization;
- arbitrary client-controlled ordering.

## 6. Alternatives

### A. Keep complete-history retrieval permanently

Pros: simplest contract and no pagination state.

Cons: response size grows with lifecycle history and gives no bounded retrieval mechanism.

### B. Offset/page-number pagination

Pros: familiar API model.

Cons: offset becomes less meaningful for an append-only sequence and can require scanning/skipping records as history grows.

### C. Sequence-cursor pagination

Pros: aligns directly with the authoritative immutable history sequence, avoids offset semantics, and supports deterministic continuation.

Cons: slightly more explicit client state and requires a clear cursor contract.

### D. Time-based pagination

Pros: intuitive for human-readable operational timelines.

Cons: timestamps are not the authoritative ordering key and may collide; using time as the cursor would duplicate ordering semantics outside the store.

## 7. Proposed Direction

The preferred candidate for evaluation is sequence-cursor pagination over the existing ascending lifecycle sequence.

The application capability should remain responsible for query validation and read-model composition. The store should remain responsible for efficient retrieval using the persisted sequence.

The API should expose a bounded page size and a continuation cursor while keeping sequence ascending and authoritative.

The dashboard should consume the same read model and must not implement pagination against SQLite or reconstruct history locally.

This is a design candidate, not an implementation authorization.

## 8. Open Questions

1. Should the first page default to the earliest transitions or the latest transitions?
2. Should the cursor represent the last returned sequence, the next sequence, or an opaque encoded token?
3. What maximum page size is appropriate for the MVP?
4. Should the API expose total history count, or only `has_more`/continuation metadata?
5. Should the dashboard use explicit “Load more” interaction, or should pagination remain API-only initially?
6. Should filtering by transition state/reason be part of M46, or should M46 remain pagination-only?
7. Is the existing SQLite index sufficient for the selected query pattern, or is a dedicated history index justified?
8. What compatibility guarantee is required for clients using the current complete-history endpoint?

## 9. Proposed Invariants

- persisted sequence remains the sole ordering authority;
- no lifecycle history is synthesized or rewritten;
- authorization remains identical to M45;
- one execution remains the query scope;
- page size is bounded;
- invalid pagination input fails explicitly;
- pagination does not mutate workflow state;
- existing clients are not silently given a different ordering;
- store-level retrieval remains the source of truth.

## 10. TDD Acceptance Shape

If the design is accepted, tests should cover at minimum:

- default bounded retrieval;
- explicit page size;
- first page ordering;
- continuation from a sequence cursor;
- final page without continuation;
- invalid/negative cursor;
- page-size bounds;
- empty history;
- unknown execution;
- owner/global authorization;
- another-user rejection;
- stable sequence ordering across repeated reads;
- restart preserving pagination results;
- no mutation caused by reads;
- API transport mapping without reconstructing history.

## 11. Design Gate Decision

**Status: Proposed — implementation is not authorized yet.**

The next action is to resolve the open questions and record an accepted M46 decision before implementation.

M45 remains complete and unchanged while this gate is evaluated.