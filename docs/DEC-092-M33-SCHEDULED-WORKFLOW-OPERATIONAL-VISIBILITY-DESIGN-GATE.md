# DEC-092 — M33 Scheduled Workflow Operational Visibility Design Gate

**Status:** Accepted  
**Date:** 2026-09-19  
**Milestone:** M33 — Scheduled Workflow Operational Visibility

## 1. Problem

M30–M32 established a durable scheduled-workflow lifecycle, interruption detection, explicit recovery, and automatic startup resume.

The system can now execute and recover scheduled workflows, but the current project does not yet define a dedicated read-side capability for answering operational questions such as:

- What scheduled workflow executions exist?
- Which execution is running, completed, failed, or interrupted?
- When did an occurrence start and finish?
- Which occurrence was recovered after restart?
- What was the last known failure reason?

Without an explicit boundary, these questions risk leaking persistence details into the API/dashboard or encouraging ad-hoc inspection logic.

## 2. Desired Outcome

Introduce a provider-neutral, read-only application capability that exposes scheduled workflow execution state without changing workflow execution, recovery, scheduling, notification, or analytical behavior.

The capability should make workflow lifecycle state observable while preserving existing ownership boundaries.

## 3. Proposed Boundary

```
ScheduledWorkflowExecutionStore
          ↓
GetScheduledWorkflowExecutions
          ↓
Read Model
          ↓
HTTP / Dashboard (future transport)
```

The application capability owns selection and presentation-oriented composition. Persistence remains behind the existing store contract.

## 4. In Scope

- read-only workflow execution query contract;
- deterministic ordering;
- explicit lifecycle-state representation;
- filtering by workflow/occurrence when the existing persistence model supports it;
- preserving execution identity and occurrence identity;
- exposing timestamps and durable state already owned by the workflow model;
- failure/recovery information already persisted;
- unit tests for the read-side capability;
- keeping the capability independent of FastAPI, React, scheduler implementation, and notification providers.

## 5. Out of Scope

- changing workflow execution semantics;
- changing recovery behavior;
- replaying executions;
- adding new scheduler behavior;
- notification delivery;
- trading decisions;
- analytical calculations;
- new persistence schema unless the existing store cannot satisfy the accepted read contract;
- authentication/authorization;
- real-time streaming;
- distributed workers or locks.

## 6. Alternatives

### A. Read persistence directly from API/dashboard

Rejected as a boundary violation. Transport and UI would become coupled to storage representation.

### B. Add query methods to the existing scheduler

Rejected because scheduling and read-side observation are separate responsibilities.

### C. Dedicated application read capability

Preferred candidate because it creates an explicit application boundary while reusing existing persisted lifecycle data.

### D. Add a separate operational database

Rejected for M33 because there is no demonstrated need for a second source of truth.

## 7. Accepted Decisions

1. **History scope:** The MVP exposes all persisted scheduled workflow executions. The current store is a small operational history and there is no demonstrated need for pagination or retention semantics yet.
2. **Ordering:** Results are ordered by `created_at DESC, execution_id DESC`. This makes the newest execution first while the UUID provides a deterministic tie-breaker.
3. **Filtering:** The MVP supports an optional exact `occurrence_id` filter because occurrence identity is already a persisted domain concept. A workflow filter is deferred because the current persistence model does not persist a separate workflow identifier.
4. **Recovery metadata:** Recovery is represented only through the persisted lifecycle state and timestamps already owned by `ScheduledWorkflowExecution`. M33 does not add a synthetic recovery flag or reconstruct historical transitions that are not persisted.
5. **Read model:** The minimum read model preserves execution id, occurrence id, lifecycle state, created/updated timestamps, analysis state, and delivery state. It is an application read model, not an operational dashboard contract.
6. **Empty result:** No matching executions is a valid empty collection.
7. **Persistence sufficiency:** The existing SQLite schema already contains the fields required by the accepted read model. M33 only adds a read/query operation to the existing store boundary; no schema migration or second operational store is required.
8. **HTTP boundary:** HTTP exposure is deferred to a separate transport design gate. M33 establishes the application read capability only.

## 8. Proposed Invariants

1. The capability is read-only.
2. It never changes workflow state.
3. It does not recalculate workflow outcomes.
4. It does not execute or recover workflows.
5. It does not depend on FastAPI, React, or scheduler implementation details.
6. It preserves persisted execution identity and occurrence identity.
7. Ordering is deterministic.
8. Missing executions produce an empty result rather than an exception.
9. Persistence remains the source of truth.
10. No second operational source of truth is introduced.
11. M33 does not invent recovery history that the persistence model does not record.

## 9. TDD Acceptance Shape

Before implementation is authorized, tests should define:

- empty execution history;
- one persisted execution;
- multiple executions with deterministic newest-first ordering;
- lifecycle-state preservation;
- execution and occurrence identity preservation;
- analysis and delivery state preservation;
- exact occurrence filtering;
- behavior when a filter matches nothing;
- no mutation of persisted state;
- store failure propagation semantics.

## 10. Design Gate Decision

**Status: Accepted — implementation is authorized for the M33 application read capability defined here.**

The implementation boundary is:

```
ScheduledWorkflowExecutionStore
          ↓
GetScheduledWorkflowExecutions
          ↓
Read Model
```

The capability remains provider-neutral and read-only. It does not introduce HTTP, dashboard, scheduler, notification, recovery, or persistence-schema behavior.

## 11. Revisit Conditions

Revisit this gate if:

- the existing workflow persistence cannot support the required read model;
- user-facing requirements require real-time updates;
- operational requirements require metrics/tracing rather than application read models;
- authentication or multi-user visibility becomes part of the requirement;
- distributed execution is introduced.
