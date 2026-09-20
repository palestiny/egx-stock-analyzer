# DEC-106 — M45 Scheduled Workflow Lifecycle History Visibility Design Gate

**Status:** Accepted  
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

## 8. Accepted Decisions

1. **Visibility:** expose history for both system/global and user-owned executions. Reuse the existing ownership/authorization boundary exactly: operator access for global records and owner access for user-owned records.
2. **Missing execution:** return a dedicated application not-found error, mapped by the API to HTTP 404. An empty history must not represent a missing execution.
3. **No history:** return an empty immutable history collection for a valid execution with no persisted history. This accommodates legacy/incomplete records without inventing or rewriting history.
4. **Transition reason:** expose the persisted transition reason unchanged. M44 lifecycle reasons are application-controlled lifecycle metadata, not arbitrary exception text.
5. **Transport/presentation:** include both the read-only API endpoint and dashboard presentation in M45. The dashboard renders the application read model only.
6. **Pagination:** defer pagination. The MVP returns the complete history for one execution because history is scoped to one execution and the lifecycle sequence is bounded by the current M44 state machine.
7. **Ordering:** sequence order is fixed ascending and authoritative. Clients cannot request alternative ordering.
8. **Initial transition:** expose `from_state = null` for the initial CREATED transition exactly as persisted by M44.

## 9. Final Boundary

```
HTTP / Dashboard
       ↓
GetScheduledWorkflowExecutionHistory
       ↓
ScheduledWorkflowExecutionStore
       ↓
SQLite lifecycle history
```

The application capability owns lookup, authorization, and immutable read-model mapping. The store owns persistence and authoritative sequence ordering. API and dashboard layers remain transport/presentation only.

## 10. Accepted Invariants

- history is read-only;
- persisted sequence is authoritative;
- no history is synthesized from current state;
- authorization is identical to the existing execution ownership boundary;
- API/dashboard do not access SQLite directly;
- lifecycle mutation remains owned by existing execution capabilities;
- history order is deterministic;
- historical records are never modified by the read capability.

## 11. TDD Acceptance Shape

- existing execution with multiple transitions returns all transitions in sequence order;
- initial CREATED transition is represented correctly;
- transition reasons are preserved;
- restart does not change returned history;
- unknown execution returns not-found;
- system-owned execution follows existing operator/global authorization semantics;
- user-owned execution is readable only by its owner;
- valid execution with no history returns an empty history collection;
- history is returned in fixed ascending sequence order;
- transition reasons are mapped without reconstruction;
- user-owned execution cannot be read by another user;
- the read capability performs no mutation;
- API transport maps the application result without recalculating or reconstructing history.

## 12. Design Gate Rule

**Status: Accepted — implementation is authorized for the M45 MVP defined here.**

The implementation remains read-only and must not expand into workflow analytics, replay, event sourcing, lifecycle mutation, or a new persistence schema.

The next implementation should remain a read-side slice only. It must not expand into workflow analytics, replay, event sourcing, or lifecycle mutation.
