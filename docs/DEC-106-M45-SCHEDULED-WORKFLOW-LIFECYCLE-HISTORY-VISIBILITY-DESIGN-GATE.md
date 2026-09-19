# DEC-106 — M45 Scheduled Workflow Lifecycle History Visibility Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M45

## 1. Problem

M44 now persists append-only lifecycle history for scheduled workflow executions, including state transitions, timestamps, and transition reasons.

The existing operational visibility capability exposes the current execution state, but it does not expose the durable lifecycle history that now exists.

M45 should define a read-only history projection without moving lifecycle semantics into API or dashboard code.

## 2. Desired Outcome

A caller should be able to request the lifecycle history of one scheduled workflow execution and receive execution identity, ordered lifecycle transitions, previous state, new state, transition timestamp, and optional transition reason.

The result must preserve the authoritative persisted sequence.

## 3. Proposed Boundary

    HTTP / Dashboard
           ↓
    GetScheduledWorkflowExecutionHistory
           ↓
    ScheduledWorkflowExecutionStore
           ↓
    SQLite lifecycle history

## 4. In Scope

- dedicated read-side application capability;
- immutable history read model;
- execution lookup by UUID;
- authoritative sequence ordering;
- ownership/authorization reuse from the existing scheduled-workflow visibility boundary;
- not-found semantics;
- empty-history semantics for legacy/incomplete records;
- application/API contract tests;
- dashboard presentation only if explicitly accepted as part of the implementation slice.

## 5. Out of Scope

- changing lifecycle transitions;
- rewriting history;
- deleting history;
- event replay;
- workflow mutation;
- retry/recovery semantics;
- new authentication model;
- analytics or aggregation across executions;
- distributed tracing;
- event sourcing migration;
- changing SQLite schema introduced by M44.

## 6. Alternatives

### A. Extend the existing current-state read model

Pros: fewer application types.

Cons: mixes current-state and historical concerns and makes the current execution contract grow around a different read shape.

### B. Dedicated GetScheduledWorkflowExecutionHistory capability

Pros: clear read-side responsibility, reuses the existing store, keeps current-state visibility stable, independently testable.

Cons: adds a small application read model and endpoint.

### C. Read history directly from API/dashboard

Rejected for the architecture boundary because transport/presentation must not own persistence semantics.

## 7. Proposed Direction

Use a dedicated application capability named GetScheduledWorkflowExecutionHistory.

It should:

1. load the execution through the existing store;
2. authorize access using the existing ownership boundary;
3. load lifecycle history through the same store;
4. return an immutable ordered read model;
5. expose no mutation capability.

The store remains the source of truth for history sequence and transition data.

## 8. Open Questions

Before implementation, the following must be explicitly resolved:

1. Should the MVP expose history for both operator/global executions and user-owned executions using the existing ownership rules?
2. Should a missing execution return the same not-found application error used by current workflow visibility?
3. Should a valid execution with no history be an empty result or a data-integrity error?
4. Should the API expose the internal transition reason verbatim or a constrained safe reason value?
5. Should M45 include an API endpoint only, or API + dashboard presentation?
6. Should history pagination be introduced now, or should the MVP return the complete history for one execution?
7. Should history ordering be fixed as ascending sequence only, or allow client ordering?
8. Should the read model expose from_state = null for the initial CREATED transition?

## 9. Proposed Invariants

- history is read-only;
- persisted sequence is authoritative;
- no history is synthesized from current state;
- authorization is identical to the existing execution ownership boundary;
- API/dashboard do not access SQLite directly;
- lifecycle mutation remains owned by existing execution capabilities;
- history order is deterministic;
- historical records are never modified by the read capability.

## 10. TDD Acceptance Shape

- existing execution with multiple transitions returns all transitions in sequence order;
- initial CREATED transition is represented correctly;
- transition reasons are preserved;
- restart does not change returned history;
- unknown execution returns not-found;
- system-owned execution follows existing operator/global authorization semantics;
- user-owned execution cannot be read by another user;
- the read capability performs no mutation;
- API transport maps the application result without recalculating or reconstructing history.

## 11. Design Gate Rule

Implementation is not authorized by this proposed gate until the open questions and final boundary are explicitly accepted and documented.

The next implementation should remain a read-side slice only. It must not expand into workflow analytics, replay, event sourcing, or lifecycle mutation.
