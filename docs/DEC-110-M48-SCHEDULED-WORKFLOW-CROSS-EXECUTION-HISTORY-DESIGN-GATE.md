# DEC-110 — M48 Scheduled Workflow Cross-Execution History Query Design Gate

**Status:** Accepted  
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

## 8. Accepted Decisions

### 8.1 Result Shape

The query returns persisted lifecycle-history events, not one summary row per execution.

Each item contains:
- execution ID;
- occurrence ID;
- sequence;
- from state;
- to state;
- occurred-at timestamp;
- persisted transition reason.

This preserves the existing M45 history read model while adding execution scope to the result.

### 8.2 Ownership Scope

Visibility exactly reuses the existing ownership boundary:

- an authenticated user sees lifecycle history only for executions owned by that user;
- the legacy/operator identity sees system/global executions where `owner_user_id IS NULL`;
- user-owned executions are not exposed to the operator compatibility identity;
- disabled/deleted users cannot authenticate, so their historical user-owned executions remain persisted but are not exposed through the authenticated user surface.

No new ownership semantics are introduced.

### 8.3 Global/System Records

Global/system executions are visible only through the existing operator/global authorization path. They are not mixed into user-owned result sets.

The cross-execution query therefore always operates over one effective visibility scope determined by the authenticated identity.

### 8.4 State Filters

The query reuses the M47 typed `from_state` and `to_state` filters.

Filtering occurs in persistence before pagination. Invalid states remain application-level validation errors.

### 8.5 Deterministic Ordering

Cross-execution history is ordered newest-first using:

```
occurred_at DESC,
execution_id DESC,
sequence DESC
```

The full ordering tuple is the authority for deterministic pagination.

### 8.6 Pagination

Pagination uses an opaque composite cursor representing the last returned ordering tuple plus the complete effective filter shape.

The cursor is bound to:
- from_state;
- to_state;
- occurred_from / occurred_to when those filters exist;
- the ordering version/shape required by the implementation.

A cursor from one query shape cannot be reused with another query shape.

Default page size remains 50 and maximum page size remains 100, matching the established history-query boundary.

### 8.7 Execution ID Narrowing

An execution ID filter is not added to the cross-execution capability.

A single-execution request already has the established M45/M46/M47 capability. Adding an execution ID to the new cross-execution contract would create overlapping semantics without adding useful capability.

### 8.8 Dashboard Scope

M48 is application/API focused. The dashboard does not gain a second cross-execution history surface in this milestone.

The existing single-execution dashboard history remains unchanged. A dashboard-wide operational history view requires a separate presentation design decision after the API contract proves useful.

### 8.9 SQLite Query and Index Strategy

The first implementation starts with the existing lifecycle-history schema and no mandatory new secondary index.

The implementation must capture representative SQLite query-plan evidence for the selected cross-execution query and pagination shape. A secondary index is introduced only if the evidence demonstrates a meaningful need under the expected query pattern.

The primary key on `(execution_id, sequence)` remains authoritative for single-execution history; M48 does not repurpose it as a cross-execution ordering contract.

### 8.10 Read-Only and Restart Semantics

The capability remains strictly read-only. It does not mutate lifecycle state, history, ownership, or cursors.

Restart consistency is inherited from the durable SQLite lifecycle-history source of truth and must be covered by integration tests.

## 9. Proposed Invariants

- reads never mutate lifecycle state or history;
- ownership authorization is evaluated before records become visible;
- one execution's history cannot leak into another user's result set;
- user queries contain only user-owned executions;
- operator/global queries contain only system/global executions;
- ordering is deterministic and documented;
- pagination is bounded;
- cursors are opaque and bound to their effective query shape;
- M45/M46/M47 single-execution behavior remains unchanged;
- lifecycle transition values remain typed and validated;
- transition-reason text is diagnostic data, not a stable search contract;
- SQLite remains an implementation detail behind the store boundary.

## 10. TDD Acceptance Shape

If M48 is implemented, tests must cover at minimum:

- empty cross-execution result;
- multiple executions with deterministic newest-first ordering;
- user ownership isolation;
- global/system visibility isolation;
- disabled/deleted-user access behavior;
- state filtering;
- bounded pagination;
- composite cursor continuation;
- cursor/query-shape mismatch;
- unknown or invalid filters;
- restart consistency;
- no mutation during reads;
- API transport;
- representative SQLite query-plan evidence;
- preservation of the existing single-execution history contract.

## 11. Design Gate Decision

**Status: Accepted — implementation is authorized for the bounded M48 scope defined above.**

Implementation must remain read-only, preserve the existing ownership boundary, reuse M47 filters, and keep the existing single-execution history contract backward compatible.

See `docs/DECISION_LOG.md` for the project decision history.
