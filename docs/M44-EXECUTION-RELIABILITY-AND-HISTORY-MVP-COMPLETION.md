# M44 — Execution Reliability & History MVP Completion

**Date:** 2026-09-19  
**Status:** Complete

## Scope

M44 hardened the durable scheduled-workflow execution boundary established by M30–M32.

The implementation adds:

- atomic occurrence reservation in SQLite;
- deterministic request fingerprints for idempotency;
- conflict detection when the same occurrence is reused with different request parameters;
- atomic concurrent start claiming;
- optimistic revision checks for stale writers;
- append-only lifecycle history;
- atomic current-state + history persistence;
- restart-safe lifecycle history;
- targeted concurrency, idempotency, revision, and failure-atomicity tests.

## Application Boundary

The existing application flow remains authoritative:

```
RunDurableScheduledWorkflow
        ↓
ScheduledWorkflowExecutionStore
        ↓
SQLite current state + lifecycle history
```

The M44 implementation does not introduce a new API/dashboard workflow model.

## Accepted Reliability Semantics

### Idempotency

An occurrence ID identifies one scheduled workflow occurrence.

The request fingerprint binds the occurrence to its normalized occurrence ID, analysis date, and effective owner identity.

- same occurrence + same fingerprint → existing execution is reused;
- same occurrence + different fingerprint → explicit idempotency conflict;
- concurrent same-occurrence creation → one durable execution reservation.

### Start Claiming

Starting a CREATED execution is an atomic database operation guarded by the current state and revision. Only the caller that successfully claims the CREATED row executes the scheduled operation.

### Optimistic Concurrency

Every persisted execution transition carries a monotonically increasing revision.

A stale writer cannot overwrite a newer persisted state. Replaying the exact already-persisted state is idempotent; conflicting or stale revisions are rejected.

### Lifecycle History

Lifecycle state transitions are recorded append-only with sequence, previous state, new state, timestamp, and optional transition reason.

Current state and its corresponding history record are persisted atomically.

### Recovery

Recovery persists the INTERRUPTED → RUNNING transition before replaying the scheduled operation. Subsequent outcome and terminal transitions therefore preserve the same revision/history contract as normal execution.

## Validation

GitHub Actions Run #1686 completed successfully for implementation head `bd74921e9c789e95b2198ab82acdded6bab689bc` after targeted fixes.

Validated areas include:

- Python unit/integration test suite;
- frontend tests;
- frontend production build;
- concurrent same-occurrence reservation;
- concurrent execution claiming;
- idempotency conflicts;
- stale revision rejection;
- repeated-save idempotency;
- lifecycle-history persistence across restart;
- atomic rollback when history persistence fails.

The pre-fix implementation had 5 CI failures related to recovery revision persistence and one incorrect history-reason assertion. Those were corrected before merge.

## Merge

Implemented in PR #102:

`feat(m44): harden execution idempotency and durable history`

Merged into `main` after GitHub Actions Run #1686 passed.

## Non-Goals

M44 does not introduce:

- distributed workers;
- queues;
- API redesign;
- dashboard redesign;
- automatic retry policy;
- portfolio/trading behavior;
- new authentication semantics;
- a second execution persistence technology.

## Result

The scheduled-workflow execution boundary now has explicit durable semantics for duplicate requests, concurrent starts, stale writes, lifecycle history, restart recovery, and atomic persistence. Future reliability work should build on these contracts rather than bypassing the execution store.
