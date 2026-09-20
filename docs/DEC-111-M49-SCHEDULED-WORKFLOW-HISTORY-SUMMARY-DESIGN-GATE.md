# DEC-111 — M49 Scheduled Workflow History Summary Design Gate

**Status:** Proposed  
**Date:** 2026-09-20  
**Milestone:** M49

## Context

M45–M48 established a durable, read-only lifecycle-history model for scheduled workflow executions:

- M45 exposes one execution's lifecycle events.
- M46 adds bounded sequence-cursor pagination.
- M47 adds typed lifecycle-state filtering.
- M48 adds UTC time filtering and bounded cross-execution event visibility.

The current read surfaces intentionally expose lifecycle events as events. The next useful read-side capability is to derive a compact execution summary from those authoritative persisted records without creating a second source of workflow truth.

## Problem

Operational consumers can currently answer:

> What lifecycle events exist?

They still have to reconstruct common execution-level facts themselves:

- when the execution started;
- when it reached a terminal state;
- how long it took;
- how many lifecycle transitions occurred;
- whether it was interrupted or recovered;
- what the final analysis/delivery states were.

Reconstructing these facts in API or dashboard code would duplicate workflow semantics and make each consumer responsible for interpreting lifecycle history.

## Goal

Define a read-only application capability that derives an immutable summary for each visible scheduled workflow execution from the existing authoritative execution state and lifecycle history.

The MVP should make common operational facts directly consumable while preserving the existing event-history capabilities unchanged.

## Scope

### In scope

- execution-level summary read model;
- start/end timestamps derived from lifecycle history;
- elapsed duration;
- final workflow state;
- analysis and delivery states;
- lifecycle transition count;
- interruption/recovery-related transition counts where derivable from persisted states;
- existing ownership authorization;
- deterministic ordering;
- testability;
- reuse of the existing ScheduledWorkflowExecutionStore boundary.

### Explicitly out of scope

- changing workflow lifecycle semantics;
- writing or mutating history;
- new workflow states;
- new persistence tables;
- retention/deletion;
- replay or recovery actions;
- predictive analytics;
- performance scoring;
- success-rate/business KPIs;
- cross-user aggregation;
- dashboard redesign;
- real-time streaming;
- distributed execution;
- AI interpretation.

## Architectural Boundary

Proposed boundary:

```
HTTP / Dashboard
       ↓
GetScheduledWorkflowExecutionSummaries
       ↓
ScheduledWorkflowExecutionStore
       ↓
Existing execution + lifecycle history
```

The summary capability is read-side only. It must not become a second workflow-state authority.

## Authoritative Data

The existing persisted sources remain authoritative:

1. ScheduledWorkflowExecution for current state, created/updated timestamps, owner, analysis state, and delivery state.
2. scheduled_workflow_execution_history for lifecycle transition sequence, timestamps, and reasons.

No duplicated summary state is persisted in M49.

## Proposed Read Model

A summary candidate is:

```
ScheduledWorkflowExecutionSummary
- execution_id
- occurrence_id
- owner_user_id (subject to existing visibility boundary)
- current_state
- analysis_state
- delivery_state
- started_at
- completed_at
- duration
- transition_count
- interruption_count
- recovery_count
```

Definitions must be explicit before implementation:

- started_at: timestamp of the first persisted transition into RUNNING; null if the execution never reached RUNNING.
- completed_at: timestamp of the terminal transition; null while non-terminal.
- duration: completed_at minus started_at; null when either endpoint is unavailable.
- transition_count: number of persisted lifecycle-history rows for the execution.
- interruption_count: number of transitions whose to_state is INTERRUPTED.
- recovery_count: number of transitions whose to_state is RUNNING while the preceding persisted state is INTERRUPTED.

The summary does not infer success from duration or transition counts. The persisted workflow state remains authoritative.

## Ordering

The MVP should use the existing deterministic execution ordering:

```
created_at DESC, execution_id DESC
```

The summary capability should preserve the same ordering as the underlying execution list unless a later design explicitly introduces another query contract.

## Ownership

Visibility must reuse the existing ownership boundary:

- authenticated users see only executions they own;
- the legacy/operator identity sees only system/global executions;
- the summary capability must not introduce a new authorization rule.

The summary must not expose events or derived information from executions the caller cannot already see.

## Alternatives

### A — Compute summaries in the dashboard

Trade-offs:

- no new backend capability;
- but duplicates lifecycle interpretation in the client;
- creates a second implementation of workflow semantics;
- makes future clients inconsistent.

Assessment: Not selected.

### B — Extend GetScheduledWorkflowExecutions with summary fields

Trade-offs:

- fewer application classes;
- reuses an existing execution-list contract;
- but mixes the existing execution-list contract with derived lifecycle analytics;
- increases coupling between a basic execution read model and history interpretation.

Assessment: Viable, but requires a broader contract change.

### C — Dedicated summary application capability

GetScheduledWorkflowExecutionSummaries

Trade-offs:

- explicit responsibility;
- keeps event history and derived summaries separate;
- easier to test and evolve;
- adds one read-side application capability and potentially one API contract.

Assessment: Preferred candidate.

### D — Persist summary columns

Trade-offs:

- faster reads after precomputation;
- but creates another state representation that can diverge from authoritative history;
- requires lifecycle-write changes and consistency guarantees.

Assessment: Deferred. M49 should derive summaries on read.

## Open Questions

1. Should the MVP expose one summary per visible execution, or also provide aggregate totals across the result set?
2. Should the API reuse the existing execution-list endpoint or introduce a dedicated summary endpoint?
3. Should summary filtering reuse all M48 cross-execution filters, or initially inherit only the existing execution-list visibility/order contract?
4. Should completed_at mean any terminal transition or only COMPLETED / COMPLETED_WITH_ERRORS / FAILED?
5. Should an execution that is currently INTERRUPTED have a partial duration ending at interruption time, or a null duration because it has not reached a terminal state?
6. Should recovery_count count every INTERRUPTED → RUNNING transition, including future recovery mechanisms?
7. What representative query-plan evidence is required before introducing any SQLite index for summary reads?
8. Should the dashboard/API be part of the first implementation slice, or should M49 establish only the application read model first?

## Proposed Invariants

1. Existing lifecycle history remains the authoritative event source.
2. Summary data is derived, not independently persisted.
3. Summary calculation cannot mutate workflow state.
4. Ownership authorization is unchanged.
5. Existing M45–M48 history contracts remain compatible.
6. Terminal/current state comes from the persisted execution model/history, not heuristic inference.
7. Deterministic ordering is preserved.
8. No business-performance or predictive interpretation is introduced.

## TDD Acceptance Shape

Before implementation, tests should cover at least:

- execution that completes normally;
- execution with analysis failure / COMPLETED_WITH_ERRORS;
- execution that fails;
- execution interrupted during startup recovery;
- interrupted execution subsequently recovered;
- execution that never reaches RUNNING;
- correct start/end/duration semantics;
- transition count;
- interruption and recovery counts;
- ownership visibility;
- deterministic ordering;
- multiple executions with identical timestamps;
- compatibility with existing lifecycle-history records;
- absence of persisted duplicate summary state.

## Design Gate Decision

**Status: Proposed — implementation is not authorized by this document yet.**

The open questions above must be resolved and the accepted contract recorded before implementation.

## Revisit Conditions

Revisit this gate if:

- workflow lifecycle semantics change;
- summary requirements become business analytics rather than operational visibility;
- persistent aggregation becomes necessary because measured query performance requires it;
- retention or archival changes the authoritative history source;
- distributed execution introduces additional lifecycle event sources.
