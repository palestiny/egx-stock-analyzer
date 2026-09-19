# DEC-090 — M31 Durable Scheduled Workflow Recovery Design Gate

**Status:** Accepted  
**Date:** 2026-09-19  
**Milestone:** M31

## Context

M30 made scheduled workflow execution durable and explicitly recoverable as an INTERRUPTED state, but deliberately stopped short of automatic replay.

The remaining operational gap is explicit recovery of an interrupted occurrence. A durable workflow that can detect interruption but cannot safely resume leaves recovery as a manual operational concern.

M31 defines a bounded recovery capability without turning the system into a distributed job platform.

## Problem

An interrupted scheduled occurrence may have completed some external side effects before the process stopped. Automatic replay therefore cannot simply execute the entire workflow again without relying on existing idempotency boundaries.

## Desired Outcome

Provide an explicit, idempotent application command to recover one persisted INTERRUPTED scheduled workflow execution.

Recovery must be observable, bounded, and safe to retry. It must reuse the existing M29 analysis-and-delivery workflow and existing durable idempotency boundaries.

## Scope

### In scope
- explicit recovery of one interrupted workflow execution;
- recovery eligibility validation;
- recovery state transition semantics;
- reuse of the existing scheduled workflow;
- idempotent recovery;
- persistence of recovery outcome;
- deterministic tests;
- restart/recovery integration tests.

### Explicitly out of scope
- automatic background resume;
- distributed locks;
- multiple workers;
- queues;
- parallel execution;
- provider retry policy;
- new notification channels;
- user-specific recovery policy;
- trading;
- portfolio allocation;
- AI decisions.

## Architectural Boundary

Recovery Command → Scheduled Workflow Recovery → ScheduledWorkflowExecutionStore → Existing M29 Scheduled Analysis + Delivery Workflow

Recovery is an explicit application capability. It is not scheduler behavior and is not embedded inside the analysis pipeline.

## Accepted Decisions

### 1. Recovery Trigger

Recovery is explicit and targeted to one workflow execution ID. M31 does not automatically resume interrupted executions during startup or scheduler ticks.

### 2. Eligibility

Only INTERRUPTED executions are recoverable. CREATED, RUNNING, COMPLETED, COMPLETED_WITH_ERRORS, and FAILED executions are rejected.

### 3. Recovery Identity

Recovery reuses the existing workflow execution identity. It does not create a new scheduled occurrence or a second durable workflow record.

### 4. Recovery Transition

An eligible INTERRUPTED execution transitions to RUNNING before replay. Successful replay reaches the established terminal states. If the process interrupts again, existing M30 recovery detection may mark RUNNING as INTERRUPTED again.

### 5. Replay Semantics

M31 reuses the existing M29 workflow as the replay operation. It does not introduce step-level checkpointing.

Recovery re-executes the configured market-analysis-and-delivery workflow while relying on existing idempotency boundaries: analysis persistence replaces the latest result per stock, and alert delivery uses M25 durable snapshot/channel idempotency.

### 6. Analysis and Delivery Independence

Recovery preserves the existing separation between analysis and delivery outcomes. Delivery failure must not be reinterpreted as analysis failure.

### 7. Retry Ownership

M31 adds no provider retry policy and no second automatic retry layer. Existing workflow failure semantics remain authoritative.

### 8. Concurrency

M31 remains process-local and sequential. Recovery of the same workflow execution is guarded by persisted lifecycle state. Distributed coordination remains deferred.

### 9. API Exposure

The initial M31 slice is application-first. No HTTP endpoint is required. API exposure, if needed, receives a separate transport decision.

## TDD Acceptance Criteria

- an INTERRUPTED execution can be recovered explicitly;
- recovery reuses the same workflow execution identity;
- terminal executions cannot be recovered;
- non-interrupted executions cannot be recovered;
- recovery transitions through RUNNING;
- successful replay reaches the appropriate terminal state;
- a second recovery request after terminal completion does not execute the workflow again;
- analysis persistence remains idempotent;
- alert delivery idempotency remains authoritative;
- a second interruption can return the execution to INTERRUPTED;
- no automatic startup replay is introduced;
- no live notification provider is required by CI.

## Trade-offs

Benefits: explicit and auditable recovery, reuse of existing workflow boundaries, no distributed infrastructure, and no leakage into stock-analysis domain logic.

Costs: replay may repeat acquisition work; without checkpoints, recovery granularity is the whole M29 workflow; safe replay depends on existing idempotency guarantees.

The MVP accepts these costs rather than prematurely introducing workflow checkpointing.

## Revisit Conditions

Revisit when automatic recovery, step-level checkpoints, asynchronous steps, multiple workers, distributed coordination, non-idempotent external side effects, or user-facing recovery history becomes necessary.