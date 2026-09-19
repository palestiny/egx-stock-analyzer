# DEC-091 — M32 Automatic Scheduled Workflow Resume Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M32

## Context

M30 made scheduled workflow executions durable and detects interrupted executions. M31 added an explicit application capability to recover one INTERRUPTED execution. The remaining operational gap is that recovery currently requires an explicit operator/application command.

M32 defines the smallest automatic-resume boundary while preserving the existing durable workflow, analysis, and notification idempotency contracts.

## Problem

A process restart can leave a scheduled workflow occurrence in INTERRUPTED. Waiting for an external caller to invoke recovery creates an operational gap. Automatic resume must avoid unsafe duplicate side effects by reusing the existing M31 recovery capability and existing idempotency boundaries.

## Desired Outcome

On application startup, detect eligible interrupted scheduled workflow executions and automatically invoke the existing M31 recovery capability.

The automatic path must reuse the existing workflow execution identity, recover only persisted INTERRUPTED executions, avoid creating a new scheduled occurrence, preserve existing analysis and alert-delivery idempotency, remain sequential and process-local, and isolate recovery failures.

## Scope

### In scope
- startup-triggered automatic recovery
- discovery of persisted INTERRUPTED workflow executions
- deterministic recovery ordering
- reuse of the existing M31 recovery capability
- per-execution failure isolation
- idempotent behavior across repeated startup attempts
- deterministic tests and restart integration coverage

### Explicitly out of scope
- step-level checkpoints
- distributed locks or workers
- parallel recovery
- queue-based recovery
- automatic provider retry
- new notification channels
- recovery HTTP endpoints
- user-configurable recovery policies
- trading, portfolio allocation, or AI decisions

## Architectural Boundary

Application Startup → AutomaticWorkflowRecovery → ScheduledWorkflowExecutionStore → M31 Recovery Capability → Existing M29 Scheduled Analysis + Delivery Workflow

Startup lifecycle triggers recovery but does not own workflow business logic. The scheduler remains responsible for timing and recurrence and does not inspect workflow state or replay work.

## Proposed Decisions

### 1. Trigger
Startup is the automatic trigger. Recovery is a lifecycle concern and must not depend on the next scheduled occurrence.

### 2. Eligibility
Only persisted INTERRUPTED executions are eligible. RUNNING executions are handled by M30 interruption detection rather than replayed directly.

### 3. Ordering
Recover interrupted executions deterministically by scheduled occurrence identity ascending, with workflow execution ID as a stable tie-breaker.

### 4. Failure Isolation
Attempt each interrupted execution independently. One recovery failure must not prevent subsequent eligible executions from being attempted.

### 5. Idempotency
Automatic recovery delegates to M31 rather than implementing a second recovery state machine. Terminal executions are not replayed. If recovery is interrupted again, M30 may return it to INTERRUPTED for a later startup.

### 6. Concurrency
Recovery remains sequential and process-local. Multi-process coordination requires a future design gate.

### 7. Startup Failure Policy
Failure to inspect the durable workflow store is an application startup failure because safe recovery eligibility cannot be established. An individual recovery failure does not fail startup; it remains attached to that execution.

### 8. API Exposure
No HTTP endpoint is introduced. Automatic recovery is a lifecycle/application concern, not a transport operation.

## Proposed Invariants

1. Startup never creates a replacement occurrence for an interrupted execution.
2. Only INTERRUPTED executions enter automatic recovery.
3. Existing workflow execution IDs remain stable through recovery.
4. Existing analysis persistence and alert-delivery idempotency remain authoritative.
5. Recovery is sequential and deterministic.
6. One failed recovery does not block later recovery attempts.
7. Scheduler timing semantics remain unchanged.
8. No stock-analysis or scoring logic is added to recovery.
9. Repeated startup scans do not replay terminal executions.
10. Recovery does not introduce a second retry mechanism.

## TDD Acceptance Shape

- no interrupted executions → startup recovery is a no-op
- one interrupted execution → M31 recovery is invoked exactly once
- multiple interrupted executions → recovery follows deterministic order
- terminal executions are ignored
- one recovery failure does not prevent subsequent recoveries
- successful recovery preserves the original workflow execution ID
- a recovery that becomes interrupted again remains eligible for a future startup
- repeated startup after terminal completion does not replay the execution
- durable-store inspection failure is surfaced as startup failure
- no scheduler tick is required to trigger recovery
- no live notification provider is required by CI

## Trade-offs

Benefits: removes the manual operational gap, reuses accepted recovery semantics, keeps scheduler timing separate from recovery, preserves idempotency boundaries, and remains deterministic.

Costs: startup time may increase when interrupted executions exist; recovery can repeat acquisition work because M31 has no step checkpoints; correctness depends on existing idempotency; the MVP remains single-process.

## Revisit Conditions

Revisit when multiple application instances, concurrent recovery workers, step-level checkpoints, non-idempotent external side effects, configurable recovery policies, long-running startup recovery, or durable recovery history/operator controls become necessary.

## Design Gate Decision

**Status: Proposed — implementation is not authorized until the decisions above are reviewed and accepted.**