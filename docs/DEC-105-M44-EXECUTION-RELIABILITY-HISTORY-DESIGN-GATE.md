# DEC-105 — Execution Idempotency & History Reliability Design Gate

Status: Proposed
Date: 2026-09-19
Milestone: M44 — Execution Reliability & History

## Purpose

M43 is complete. The next reliability review targets the existing execution/idempotency and durable scheduled-workflow execution boundaries.

The goal is to make existing execution semantics explicit under concurrency, partial failure, restart, retry, and repeated requests before extending the system further.

This gate covers:
- idempotency correctness;
- concurrent duplicate requests;
- reserve/create race behavior;
- failure during reservation;
- failure during save;
- duplicate request after partial failure;
- key normalization and conflict semantics;
- lifecycle transition evidence;
- transition ordering;
- repeated saves;
- history persistence failure;
- retry/cancel/resume evidence.

## Current Evidence

The repository already contains ExecutionIdentity and an in-memory ExecutionRegistry, durable ScheduledWorkflowExecution, SQLite persistence, a UNIQUE occurrence_id, lifecycle states including interruption/recovery, and operational read-side access.

The current SQLite create_or_get() uses a read-before-insert. The database UNIQUE constraint is the final duplicate guard, but the race behavior is not expressed as an explicit atomic create-or-get contract.

The current scheduled-workflow record stores current state and timestamps, but not append-only lifecycle transition history. The current save() also lacks an optimistic revision check.

These are design observations; they are not claims that a production race has already been reproduced.

## Problem Statement

The system must answer:

> If the same logical request is received more than once, including concurrently or after a partial failure, exactly what execution is allowed to exist and what evidence remains?

The design must distinguish:
1. logical idempotency identity;
2. execution instance identity;
3. current execution state;
4. lifecycle transition evidence;
5. persisted outcome evidence.

## Required Review Areas

### Race / Concurrency
At most one execution identity may be created for one normalized idempotency identity. Correctness must be enforced by the persistence boundary, not by an application-level check alone.

### Failure During Reserve
The system must distinguish reservation conflict, storage failure, and successful reservation followed by response loss. A storage failure must not be interpreted as a free key unless the persistence boundary proves that no reservation committed.

### Failure During Save
A state transition must not be reported as durable when persistence failed. The contract must define retryability and recovery semantics.

### Duplicate After Partial Failure
If reserve succeeds, work begins, persistence fails, and the caller retries, the second request must resolve against durable state rather than blindly starting another execution.

### Key Normalization / Conflict
Equivalent normalized keys resolve to one logical identity. Reuse of a key with materially different request parameters must produce an explicit conflict.

### Lifecycle Ordering
The lifecycle must define a legal transition graph. Persisted transitions must preserve ordering.

### Repeated Saves
The system must distinguish idempotent replay, invalid repeated transitions, and stale writers overwriting newer state.

### History Persistence Failure
Current-state persistence and history persistence require an explicit atomicity boundary. A transition is not fully durable if required history evidence is missing.

### Retry / Cancel / Resume Evidence
Retry, cancel, interruption, and recovery must leave durable evidence of what happened, when, which execution was affected, and why when a reason exists.

## Alternatives

### A — Current State Only
Keep current state and improve idempotency.
Trade-off: smallest change, but no complete lifecycle evidence.

### B — Current State + Append-Only History
Keep the current row as the direct read model and add append-only transition history.
Trade-off: additional persistence complexity, but preserves current contracts and provides durable lifecycle evidence.

### C — Event Sourcing
Make history primary and derive current state from events.
Trade-off: strongest historical model but unnecessary architectural complexity for the current single-application requirements.

M44 candidate direction: B, pending explicit acceptance of atomicity and concurrency details.

## Proposed Decisions

### 1. Atomic Reservation
Use the database uniqueness constraint as the concurrency authority. Reservation must be one atomic database operation, not a trusted SELECT → INSERT sequence.

### 2. Idempotency Fingerprint
Store the normalized idempotency key and a deterministic request fingerprint.
Same key + same fingerprint = idempotent replay.
Same key + different fingerprint = explicit conflict.

### 3. Durable Idempotency
Idempotency for restart-surviving operations must be durable. An in-memory registry may be an optimization but cannot be the correctness boundary.

### 4. Current State + History
Persist the current execution transition and its append-only history record in one SQLite transaction.
If either fails, the transaction rolls back.

### 5. Transition Sequence
Each history record receives a monotonically increasing sequence scoped to the execution. Ordering is explicit rather than inferred from timestamps.

### 6. Optimistic Concurrency
The current execution row carries a revision. A transition must match the expected revision and atomically increment it. A stale writer fails rather than overwriting newer state.

### 7. Repeated Transition Semantics
A transition replay is safe only when it represents the same logical transition/request identity. A different transition against a stale revision is rejected.

### 8. Recovery
Recovery is itself a lifecycle transition and must be recorded. For example RUNNING → INTERRUPTED followed by INTERRUPTED → RUNNING produces two history records.

### 9. Retry / Cancel
Lifecycle-changing retry/cancel operations produce explicit transition evidence with reason/context.

### 10. History Read Model
M44 establishes persistence semantics first. A broad new dashboard/API surface is deferred to a separate presentation gate.

## Proposed Invariants

1. One normalized idempotency key cannot represent two materially different requests without explicit conflict.
2. Concurrent identical requests cannot create two execution identities.
3. A durable transition and its required history evidence commit atomically.
4. Failed persistence cannot expose a half-transition.
5. History sequence numbers are strictly ordered per execution.
6. Current revision and history sequence cannot move backwards.
7. A stale writer cannot overwrite newer state.
8. Recovery creates durable transition evidence.
9. Retry/cancel state changes create durable transition evidence.
10. Duplicate requests after partial failure resolve from durable state.
11. Current state remains directly readable without replaying the entire history.
12. Existing API/dashboard consumers are not forced to become event-sourced.

## TDD Acceptance Shape

### Idempotency
- same normalized key + same request → same execution;
- key whitespace/case normalization → same identity;
- same key + different fingerprint → conflict;
- concurrent same-key reservation → one execution;
- reservation storage failure → no ambiguous duplicate;
- duplicate after response loss → existing durable execution is resolved.

### Persistence Failure
- state save failure leaves no partial current-state/history transition;
- history save failure rolls back the current-state transition;
- retry after failed transaction is safe;
- stale revision cannot overwrite newer revision.

### History
- CREATED evidence is durable;
- RUNNING is recorded;
- terminal states are recorded;
- INTERRUPTED is recorded;
- recovery to RUNNING is recorded;
- retry/cancel transitions are recorded when they change lifecycle state;
- repeated saves do not create duplicate history for the same transition;
- ordering is deterministic by sequence;
- history survives restart.

### Integration / Concurrency
- two SQLite connections racing for one key produce one durable execution;
- duplicate after simulated partial failure does not start a second execution;
- restart preserves current state, idempotency identity, revision, and history.

## Explicit Non-Goals

No distributed queues, brokers, event sourcing, multi-node locking service, new trading behavior, analytical changes, notification-provider changes, AI behavior, broad dashboard redesign, or speculative microservices.

## Design Gate Status

Proposed. Implementation is not authorized until the concurrency, atomicity, idempotency-conflict, and history contracts are explicitly accepted.