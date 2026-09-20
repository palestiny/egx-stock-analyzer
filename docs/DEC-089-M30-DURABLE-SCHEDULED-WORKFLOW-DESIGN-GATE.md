# DEC-089 — M30 Durable Scheduled Workflow Design Gate

**Status:** Accepted  
**Date:** 2026-09-19  
**Milestone:** M30

## Context

M29 established the scheduled analysis-and-delivery workflow, but the workflow remains synchronous and process-local. A process restart can interrupt an occurrence without a durable record describing what was started, what completed, and what remains recoverable.

The project already has durable analysis-result persistence and durable alert-delivery idempotency, but those boundaries do not represent the lifecycle of the scheduled workflow itself.

## Problem

The platform needs a durable representation of scheduled workflow execution so that:

1. a scheduled occurrence has a stable identity;
2. workflow state survives process restart;
3. analysis and delivery outcomes remain independently observable;
4. a completed occurrence is not accidentally executed twice after restart;
5. an interrupted occurrence can be detected explicitly;
6. the scheduler remains responsible for timing while durable workflow state remains an application/infrastructure concern;
7. the MVP does not become a distributed job system.

## Desired Outcome

Introduce a durable scheduled-workflow execution record behind an explicit application/infrastructure boundary.

The record represents the lifecycle of one scheduled M29 workflow occurrence, not analytical results and not notification snapshots.

## Scope

### In scope

- workflow occurrence identity;
- durable lifecycle state;
- persistence of scheduled workflow state;
- explicit transition semantics;
- restart/recovery detection;
- idempotent start of an occurrence;
- deterministic tests;
- integration with the existing M29 scheduled analysis-and-delivery workflow.

### Explicitly out of scope

- distributed locks;
- multiple workers;
- queues;
- asynchronous delivery;
- provider retry;
- new notification channels;
- user-specific schedules;
- trading;
- portfolio allocation;
- AI decisions;
- replacing the existing analysis-result or alert-delivery stores.

## Architectural Boundary

```
Recurring Scheduler
        ↓
Scheduled Workflow
        ↓
Durable Workflow Execution Store
        ↓
RunConfiguredMarketAnalysis
        ↓
AutomaticAlertDelivery
```

The scheduler continues to own when an occurrence should run. The workflow owns business sequencing. The durable store owns persistence of workflow lifecycle state.

## Alternatives Considered

### A — Persist scheduler internals

Not selected. Scheduler implementation details should not become the business record of whether an application workflow occurred.

### B — Reuse AnalysisResultStore

Not selected. AnalysisResultStore represents per-stock analytical snapshots, not workflow lifecycle.

### C — Reuse AlertDeliveryStore

Not selected. AlertDeliveryStore represents notification delivery idempotency, not analysis-and-delivery workflow state.

### D — Introduce a dedicated ScheduledWorkflowExecutionStore

Selected. It gives the lifecycle a clear boundary without contaminating analytical or notification persistence models.

## Accepted Decisions

### 1. Workflow Identity

Each scheduled occurrence receives a stable UUID workflow execution ID.

The occurrence ID from the recurring scheduler remains the business idempotency key for the schedule occurrence. The workflow execution record stores both identifiers.

### 2. Lifecycle States

The MVP uses:

- CREATED
- RUNNING
- COMPLETED
- COMPLETED_WITH_ERRORS
- FAILED
- INTERRUPTED

INTERRUPTED means the process stopped after the workflow became RUNNING but before a terminal state was durably recorded. It is an explicit recovery state, not an inferred success or failure.

### 3. Durable Transition Rules

Only valid forward transitions are allowed:

```
CREATED → RUNNING
RUNNING → COMPLETED
RUNNING → COMPLETED_WITH_ERRORS
RUNNING → FAILED
RUNNING → INTERRUPTED
```

A terminal state cannot be started again.

### 4. Start Idempotency

Starting the same scheduler occurrence twice must not create two active workflow executions.

The occurrence identity is unique in persistence. A second start returns the existing execution record rather than creating a duplicate.

### 5. Restart Recovery

On application startup, any persisted RUNNING workflow execution is eligible to be marked INTERRUPTED.

M30 does not automatically resume an interrupted occurrence. Automatic resume would require new decisions around replay safety, provider side effects, and delivery semantics.

### 6. Analysis and Delivery Outcomes

The workflow record stores the aggregate analysis state and aggregate delivery state independently.

Delivery failure must never rewrite a successful analysis state.

### 7. Persistence Boundary

The first implementation uses SQLite, consistent with the project's current persistence baseline, behind a dedicated ScheduledWorkflowExecutionStore protocol.

No ORM is introduced.

### 8. Transaction Boundary

Each lifecycle transition is persisted transactionally.

The workflow does not attempt to make analysis persistence and workflow-state persistence one cross-store transaction.

### 9. Concurrency

The MVP remains process-local and sequential. SQLite uniqueness protects duplicate occurrence creation, but M30 does not claim distributed coordination.

### 10. Recovery

Recovery is explicit and observable. The MVP detects and marks stale RUNNING executions as INTERRUPTED; it does not silently resume or fabricate a terminal outcome.

## TDD Acceptance Criteria

- creating an occurrence persists a unique workflow execution;
- starting the same occurrence twice returns the same execution identity;
- valid lifecycle transitions are persisted;
- invalid transitions are rejected;
- terminal executions cannot be restarted;
- restart recovery marks RUNNING executions as INTERRUPTED;
- interrupted executions are not automatically resumed;
- analysis and delivery states are stored independently;
- delivery failure does not change analysis state;
- persistence survives store/runtime recreation;
- no duplicate active execution exists for one occurrence;
- no live notification provider is required by CI.

## Consequences

M30 adds one durable application lifecycle boundary while preserving the existing analysis-result and alert-delivery boundaries.

The immediate benefit is explicit restart safety and observable workflow lifecycle.

The trade-off is another persistence model and additional state-management code. That complexity is justified only for scheduled workflow execution and must not leak into stock-analysis domain behavior.

## Revisit Conditions

Revisit this gate when:

- multiple workers are required;
- asynchronous queues become necessary;
- interrupted-workflow automatic resume is required;
- distributed locking/coordination is required;
- user-specific schedules are introduced;
- workflow history becomes a user-facing feature.
