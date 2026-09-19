# DEC-109 — M48 Scheduled Workflow Cross-Execution History Query Design Gate

**Status:** Proposed  
**Date:** 2026-09-20  
**Milestone:** M48

## 1. Problem

M45 established lifecycle-history visibility for one scheduled workflow execution. M46 added bounded sequence-cursor pagination, and M47 added typed lifecycle-state filtering.

The current read boundary remains intentionally scoped to one execution. Operational consumers may eventually need to inspect lifecycle history across multiple executions—for example, to understand recent workflow behavior, identify repeated interruption/failure patterns, or correlate execution state transitions without opening executions one by one.

A cross-execution query changes the read shape and authorization surface, so it requires an explicit design gate before implementation.

## 2. Desired Outcome

Define whether the system should expose a bounded, read-only history query across multiple scheduled workflow executions while preserving:

- existing ownership authorization;
- durable lifecycle history as the source of truth;
- deterministic ordering;
- bounded pagination;
- typed state filtering;
- no lifecycle mutation or replay;
- thin API/dashboard transport boundaries.

This document is a design gate only. It does not authorize implementation.

## 3. Current Boundary

```
HTTP / Dashboard
       ↓
GetScheduledWorkflowExecutionHistory
       ↓
ScheduledWorkflowExecutionStore
       ↓
SQLite lifecycle history
```

M48 would introduce a separate cross-execution read capability only if the design is accepted. The existing single-execution capability must remain backward compatible.

## 4. In Scope

- cross-execution history query semantics;
- explicit execution ownership/authorization scope;
- bounded pagination;
- deterministic ordering;
- reuse or extension of M47 state filters;
- query limits and default bounds;
- application/API contract;
- dashboard presentation boundary if accepted;
- SQLite query shape and indexing evidence;
- tests for isolation and restart consistency.

## 5. Out of Scope

- lifecycle mutation;
- event replay;
- retention/deletion;
- free-text reason search;
- analytics or aggregation;
- arbitrary client-controlled ordering;
- new authentication mechanisms;
- changing ownership semantics;
- distributed search infrastructure;
- replacing SQLite.

## 6. Alternatives

### A. Keep history strictly per execution

Pros: smallest boundary and strongest locality.

Cons: operational consumers must make many requests and reconstruct cross-execution views themselves.

### B. Add a dedicated cross-execution history read capability

Pros: explicit application contract, controlled authorization, bounded query semantics, and no contamination of the existing single-execution capability.

Cons: introduces a second read model and requires careful ownership filtering and deterministic pagination.

### C. Extend the existing single-execution capability to accept optional execution collections

Pros: fewer application classes.

Cons: mixes two materially different query scopes and makes authorization, pagination, and response semantics harder to reason about.

### D. Add a generic workflow-event search abstraction

Pros: future extensibility.

Cons: introduces a broader abstraction before evidence requires it and risks turning lifecycle history into an event-search subsystem.

## 7. Candidate Direction

Candidate B is proposed for evaluation: a dedicated `GetScheduledWorkflowHistory` read capability for cross-execution queries.

The candidate would:

1. query only persisted lifecycle-history records belonging to executions visible to the authenticated identity;
2. preserve the existing owner-or-global authorization boundary;
3. reuse typed `from_state` / `to_state` filters from M47;
4. use bounded opaque pagination;
5. define one deterministic ordering authority;
6. return execution identity plus lifecycle transition information in each item;
7. remain strictly read-only.

This remains a proposal until the open questions are resolved.

## 8. Open Questions

1. Should the query return lifecycle-history events directly, or summarize one row per execution?
2. Should user-owned queries include only that user's executions while operators retain global visibility?
3. Should system/global executions be visible to all authenticated users or only the operator compatibility identity?
4. Should M48 reuse M47 `from_state` / `to_state` filters?
5. What deterministic ordering should govern cross-execution results?
6. Should pagination use a sequence cursor, a composite cursor, or another opaque cursor representation?
7. What maximum page size is appropriate?
8. Should an optional execution ID filter remain available as a narrowing constraint?
9. Should the dashboard expose cross-execution history in M48 or remain API/application-only?
10. What query/index evidence is required before introducing a secondary SQLite index?
11. How should deleted-user ownership be represented in a read model?
12. Should global/system records be mixed with user-owned records in one result set, or explicitly separated?

## 9. Proposed Invariants

- reads never mutate lifecycle state or history;
- ownership authorization is evaluated before records become visible;
- one execution's history cannot leak into another user's result set;
- ordering is deterministic and documented;
- pagination is bounded;
- cursors are opaque and bound to their effective query shape;
- M45/M46/M47 single-execution behavior remains unchanged;
- lifecycle transition values remain typed and validated;
- transition-reason text is diagnostic data, not a stable search contract;
- SQLite remains an implementation detail behind the store boundary.

## 10. TDD Acceptance Shape

If M48 is accepted, tests should cover at minimum:

- empty cross-execution result;
- multiple executions with deterministic ordering;
- user ownership isolation;
- global/system visibility;
- deleted/disabled-user semantics;
- state filtering;
- bounded pagination;
- cursor continuation;
- cursor/query-shape mismatch;
- unknown or invalid filters;
- restart consistency;
- no mutation during reads;
- API transport;
- dashboard behavior if dashboard scope is accepted;
- query behavior with sufficient evidence for the selected SQLite strategy.

## 11. Design Gate Decision

**Status: Proposed — implementation is not authorized.**

The next action is to resolve the open questions and record an accepted decision before implementing M48.

See `docs/DECISION_LOG.md` for the project decision history.
