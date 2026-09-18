# DEC-088 — M29 Scheduled Automatic Alert Delivery Design Gate

**Status:** Accepted  
**Date:** 2026-09-19  
**Milestone:** M29

## Context

M28 established an explicit post-analysis automatic-delivery capability. M19 already provides recurring full-market analysis, but its scheduler currently triggers analysis only. Scheduled notification policy was intentionally deferred from M28.

M29 defines the boundary that connects recurring full-market analysis to the existing automatic alert-delivery capability without moving notification policy into the scheduler or changing stock-analysis semantics.

## Problem

The platform needs a deterministic scheduled workflow that:

1. executes configured full-market analysis;
2. preserves existing market-analysis execution semantics;
3. invokes M28 automatic alert delivery only after analysis returns;
4. keeps delivery failures independent from analysis failures;
5. does not create a second notification policy;
6. remains synchronous and process-local for the current MVP.

## In Scope

- composition of configured-market analysis with automatic alert delivery;
- invocation timing relative to analysis completion;
- handling successful, partial, and failed market-analysis executions;
- separation of analysis and delivery outcomes;
- scheduler ownership boundary;
- recurring schedule integration;
- deterministic tests.

## Out of Scope

- new alert-generation rules;
- changes to M25 delivery persistence/idempotency;
- provider retries or queues;
- multiple channels;
- user notification preferences;
- delivery scheduling independent of analysis;
- notification analytics;
- trading behavior;
- AI notification decisions.

## Architectural Boundary

    Recurring Scheduler
            ↓
    Scheduled Analysis + Delivery Workflow
            ↓
    RunConfiguredMarketAnalysis
            ↓
    Analysis Execution
            ↓
    AutomaticAlertDelivery
            ↓
    DeliverAlert
            ↓
    NotificationProvider

The scheduler owns timing only. The workflow owns post-analysis composition. Existing capabilities retain ownership of analysis, candidate eligibility, delivery persistence/idempotency, and provider behavior.

## Alternatives

### A. Add delivery directly inside RunConfiguredMarketAnalysis

Not selected. Configured-market analysis should remain an analysis execution capability. Adding notification side effects would make its contract depend on delivery configuration.

### B. Add delivery directly inside RecurringConfiguredMarketAnalysis

Not selected. The recurring capability owns recurrence policy and delegates timing to the scheduler; it should not own notification business policy.

### C. Dedicated scheduled analysis-and-delivery workflow

Selected. A dedicated composition boundary invokes existing capabilities in sequence while preserving independent outcomes.

### D. Make the scheduler invoke analysis and delivery as two unrelated operations

Not selected. The scheduler would become responsible for workflow sequencing and could accidentally permit delivery without the corresponding analysis result.

## Accepted Decisions

### 1. Workflow Trigger

M29 introduces a dedicated application workflow that runs configured-market analysis and, after that invocation returns, passes the resulting Execution to M28 AutomaticAlertDelivery.

The workflow owns only this composition. It does not duplicate analysis or notification rules.

### 2. Delivery Eligibility

M28 remains authoritative. The workflow passes the returned analysis Execution unchanged to automatic delivery. Only successful symbols from that execution can produce candidates.

### 3. Analysis Failure Semantics

If configured-market analysis raises before returning an Execution, automatic delivery is not invoked.

If analysis returns FAILED or COMPLETED_WITH_ERRORS, the workflow still invokes M28 for successful symbols recorded in the returned execution. This preserves M28 partial-success behavior.

### 4. Independent Outcomes

The workflow returns both the analysis Execution and the AutomaticAlertDeliveryResult. Delivery failure never changes analysis execution state.

### 5. Scheduler Boundary

RecurringConfiguredMarketAnalysis remains responsible for recurrence, calendar policy, occurrence identity, overlap prevention, and timing. The scheduled operation invokes the new workflow instead of RunConfiguredMarketAnalysis directly.

The scheduler does not inspect alert candidates, delivery state, channels, or provider failures.

### 6. Execution Date

The scheduled occurrence local calendar date remains the analysis date passed to RunConfiguredMarketAnalysis. Automatic delivery does not calculate another date.

### 7. Ordering and Idempotency

M28 retains deterministic symbol ordering and M25 snapshot/channel idempotency. M29 introduces no new ordering or idempotency mechanism.

### 8. Retry

No new retry layer is introduced. Per-stock analysis retry remains inside RunStockAnalysis; notification retry remains deferred.

### 9. Manual Analysis

M29 does not change the existing manual market-analysis endpoint. Manual analysis remains analysis-only unless a future explicit workflow requests automatic delivery.

### 10. Concurrency

The workflow remains synchronous and sequential. No queue, worker, or parallel delivery model is introduced.

## TDD Acceptance Criteria

- successful configured-market analysis invokes automatic delivery exactly once with the same returned Execution;
- partial market-analysis execution still invokes automatic delivery for its successful symbols;
- failed market-analysis execution with a returned Execution still invokes automatic delivery, which becomes a no-op when there are no successful symbols;
- analysis exception before an Execution exists prevents automatic delivery;
- analysis execution state is unchanged by delivery outcome;
- delivery failure is visible in the workflow result without becoming analysis failure;
- scheduled execution invokes the workflow rather than the raw analysis use case;
- recurring scheduling semantics remain unchanged;
- no live notification provider is required by CI.

## Revisit Conditions

Revisit when scheduled delivery needs independent timing, asynchronous queues/workers, multiple channels, user-specific schedules, provider retry policies, durable workflow state, or distributed coordination.
