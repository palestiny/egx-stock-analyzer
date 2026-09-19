# DEC-105 — Execution Idempotency & History Reliability Design Gate

Status: Accepted
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

## Accepted M44 Decisions

### 1. Durable idempotency boundary

SQLite is the correctness boundary for restart-surviving idempotency. The in-memory ExecutionRegistry remains optional optimization/test infrastructure and is not authoritative.

### 2. Atomic reservation

The durable create-or-get operation will normalize the idempotency key and execute reservation in one SQLite transaction using the database UNIQUE constraint as the concurrency authority. The implementation will not depend on a separate SELECT-before-INSERT check.

A uniqueness conflict resolves to the existing durable execution. A non-conflict database failure rolls back and is surfaced as a storage failure; it must never be interpreted as an unused key.

### 3. Request fingerprint and conflict

Every durable idempotent request stores a deterministic fingerprint of the request-defining parameters.

For the scheduled workflow boundary, the fingerprint includes the normalized occurrence identity, requested analysis date, and owner identity. Same normalized key plus the same fingerprint is an idempotent replay. Same key plus a different fingerprint is an explicit conflict and must not start or mutate another execution.

### 4. Current state plus append-only history

M44 selects current-state persistence plus append-only lifecycle history rather than event sourcing.

The current execution row remains the direct read model. Each lifecycle-changing transition creates exactly one history record. Current-state and history writes commit in the same SQLite transaction.

### 5. Revision and stale-writer protection

The current execution row gains a monotonic revision. Every lifecycle mutation supplies the expected revision and atomically increments it.

An update affecting zero rows because the revision is stale is rejected as a concurrency conflict. The stale writer must not overwrite newer state.

### 6. Transition ordering

History ordering is defined by a monotonically increasing sequence scoped to the execution. Timestamps remain diagnostic metadata, not the ordering authority.

### 7. Replay / repeated-save semantics

A durable save that represents the same already-committed transition is idempotent and does not create duplicate history. A different transition using a stale revision is rejected.

This makes transport/application retries safe without allowing silent state rewrites.

### 8. Lifecycle evidence

The following transitions must be durable history evidence when they occur:

- CREATED → RUNNING;
- RUNNING → COMPLETED;
- RUNNING → COMPLETED_WITH_ERRORS;
- RUNNING → FAILED;
- RUNNING → INTERRUPTED;
- INTERRUPTED → RUNNING during recovery.

Retry/cancel operations are recorded when they change lifecycle state. Outcome-only field updates that do not change lifecycle state remain current-state updates and do not manufacture a lifecycle transition.

### 9. Persistence-failure atomicity

A current-state write and its required history write are one transaction. If either fails, neither becomes durable.

The caller receives the persistence error and may retry against the last durable revision/state. No in-memory state is treated as committed merely because the domain object was created.

### 10. Recovery and partial-failure evidence

Recovery is a normal lifecycle transition, not an out-of-band mutation. A persisted INTERRUPTED execution followed by recovery produces both transition records.

A duplicate request after response loss resolves the durable execution before any new work starts.

### 11. Terminal replay policy

For durable scheduled workflows, an existing execution for the same idempotency key and matching fingerprint is always replayed from durable state once it has left CREATED. Terminal states are therefore not silently replaced by a new execution under the same key.

This removes the current in-memory-only distinction where some terminal states can be replaced and makes durable scheduled execution semantics explicit.

### 12. History read boundary

M44 establishes durable persistence semantics and an application-level history capability. A broad new HTTP/dashboard presentation surface is deferred to a separate design gate.

## Design Gate Status

**Accepted — implementation is authorized for the M44 Execution Reliability & History MVP defined above.**


Proposed. Implementation is not authorized until the concurrency, atomicity, idempotency-conflict, and history contracts are explicitly accepted.

## 13. Repository-Level Gap Assessment

The current tests establish sequential idempotency for an in-memory registry and sequential create-or-get behavior for scheduled workflow occurrences. They do not yet establish the concurrency contract across two SQLite connections.

The current scheduled-workflow tests prove that final lifecycle state survives restart, but they do not prove an append-only transition trail exists or that transition evidence survives a history-write failure.

The current persistence implementation updates the execution row by execution ID without a revision predicate. Therefore stale-writer protection is not currently an implemented invariant.

The current in-memory ExecutionRegistry treats FAILED and COMPLETED_WITH_ERRORS as eligible for a new execution. That policy is a semantic choice and must not be assumed to be correct for every durable workflow operation. M44 must define which terminal states are replayable and which are terminal/idempotent.

The current durable occurrence identity is tied to scheduled occurrence_id. It is useful idempotency evidence for recurring scheduling, but it is not by itself a general request idempotency contract with request-parameter conflict detection.

These gaps are the reason this work is a design gate rather than an immediate refactor.
