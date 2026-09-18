# DEC-088 — M29 Automatic Alert Delivery Trigger Integration Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M29

## Context

M28 established a dedicated automatic-alert-delivery policy that consumes a completed market-analysis `Execution` and delegates eligible alert candidates to the existing M25/M26 delivery boundary.

M28 intentionally remains an explicit post-analysis capability. The system therefore has the policy, but no accepted orchestration rule yet defines when that policy should be invoked automatically as part of the application's normal full-market workflow.

M29 must decide whether and where automatic alert delivery should be triggered after market analysis, without moving notification policy into analytical components.

## Problem

Define a controlled trigger boundary that can:

1. invoke M28 after the appropriate market-analysis completion;
2. preserve analysis success independently from notification failures;
3. avoid duplicate automatic-delivery invocations for the same analysis execution;
4. remain compatible with M17/M18/M19 full-market execution and scheduling;
5. keep scheduler timing concerns separate from notification policy;
6. remain deterministic and testable.

## In Scope

- trigger ownership;
- relationship to `RunConfiguredMarketAnalysis`;
- relationship to scheduled full-market execution;
- invocation timing relative to analysis completion;
- propagation/isolation of delivery failures;
- trigger idempotency semantics;
- aggregate execution/result handling;
- composition and tests.

## Out of Scope

- changing alert-generation rules;
- changing M28 candidate selection;
- changing M25 delivery persistence/idempotency;
- provider retry/queues;
- multiple channels;
- user notification preferences;
- delivery analytics;
- trading behavior;
- AI notification decisions;
- scheduler recurrence rules.

## Current Boundary

```
Scheduler
   ↓
ScheduledConfiguredMarketAnalysis
   ↓
RunConfiguredMarketAnalysis
   ↓
RunMarketAnalysis
   ↓
RunStockAnalysis
   ↓
AnalysisResultStore

M28 remains a separate capability:
Completed Market Analysis Execution
   ↓
AutomaticAlertDelivery
```

The design question is whether an orchestration boundary should connect these two flows.

## Alternatives

### A. Invoke M28 inside RunStockAnalysis

Not selected candidate. This would make a single-stock analytical operation responsible for market-wide notification behavior and would couple analysis to external side effects.

### B. Invoke M28 inside RunMarketAnalysis

Candidate, but requires careful handling because `RunMarketAnalysis` currently owns market-wide analysis execution only. Embedding notification delivery there would make analysis execution aware of notification policy and risks changing the meaning of the use case.

### C. Invoke M28 inside RunConfiguredMarketAnalysis

Preferred candidate for evaluation. This capability already represents configured full-market execution above the reusable market-wide analysis boundary. It can coordinate the post-analysis policy without changing `RunMarketAnalysis` or `RunStockAnalysis`.

### D. Invoke M28 from the scheduler

Not selected candidate. The scheduler should remain a timing/trigger mechanism and should not own business sequencing between analysis and notification capabilities.

### E. Introduce a dedicated post-analysis workflow/orchestrator

Candidate for evaluation. This gives the cleanest separation if multiple post-analysis policies are expected, but adds another application abstraction before evidence requires it.

## Open Questions — Must Resolve Before Implementation

1. **Trigger owner:** Should `RunConfiguredMarketAnalysis` invoke M28, or should a dedicated post-analysis orchestration capability own the sequence?
2. **Invocation condition:** Should M28 run for `COMPLETED` and `COMPLETED_WITH_ERRORS` analysis executions, but not `FAILED`?
3. **Delivery failure effect:** Should delivery failure ever change the returned analysis execution state?
4. **Result shape:** Should the caller receive both the original market-analysis result and the automatic-delivery result?
5. **Idempotency:** Is M25 delivery idempotency sufficient, or does the trigger need execution-level invocation idempotency?
6. **Scheduled path:** Should scheduled full-market analysis automatically inherit the same post-analysis delivery behavior?
7. **Manual path:** Should the existing POST market-analysis command also trigger automatic delivery?
8. **Empty universe:** Should an empty completed analysis invoke M28 as a deterministic no-op?
9. **Testing boundary:** Which composition/integration tests must prove analysis and delivery failure domains remain independent?

## Proposed Invariants

1. Analytical execution remains authoritative for analysis success/failure.
2. Delivery failure never converts successful analysis into analytical failure.
3. M28 remains the only owner of automatic-delivery policy.
4. `RunStockAnalysis` remains unaware of notification delivery.
5. Scheduler remains unaware of notification eligibility and provider behavior.
6. Existing M25 idempotency remains authoritative for duplicate alert delivery.
7. The trigger must be deterministic and synchronously testable in the MVP.
8. No live notification provider is required by CI.

## TDD Acceptance Shape

- completed market analysis invokes automatic delivery exactly once at the accepted boundary;
- partial analysis invokes delivery only for successful analysis symbols;
- failed analysis does not invoke delivery;
- delivery failure does not change analysis execution state;
- the returned result preserves both analysis and delivery outcomes;
- scheduled and manual configured-market execution follow the accepted trigger policy;
- empty successful analysis remains a deterministic no-op;
- repeated execution remains safe under existing delivery idempotency;
- no analytical calculations are introduced into the trigger.

## Design Gate Decision

**Status: Proposed — implementation is not authorized yet.**

The next action is to resolve the open questions and record the accepted trigger boundary before implementation.
