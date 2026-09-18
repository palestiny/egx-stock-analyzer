# DEC-077 — M18 Scheduled Full-Market Analysis Design Gate

**Status:** Accepted  
**Date:** 2026-09-18  
**Milestone:** M18 — Scheduled Full-Market Analysis

## Context

M10 established an in-process scheduler and a scheduled-analysis trigger for an explicitly supplied set of analysis inputs. M17 now provides `RunConfiguredMarketAnalysis`, which discovers the configured universe through `StockCatalog.symbols()` and executes it through the existing M14 market-wide capability.

The next operational need is to connect those two boundaries without making the scheduler responsible for stock discovery or analytical behavior.

## Problem

The system can currently:

- execute the configured universe on demand through `POST /api/v1/market-analysis`;
- schedule operations through `Scheduler`;
- execute explicit-input scheduled analysis through `ScheduledAnalysisTrigger`.

It cannot yet schedule the configured market capability as a first-class operation.

## Desired Outcome

M18 establishes a one-shot scheduled trigger for configured-market analysis:

1. a caller schedules a configured-market execution for a specific timestamp;
2. the scheduler stores only a callable operation;
3. when due, the operation invokes `RunConfiguredMarketAnalysis`;
4. the configured capability captures the current catalog snapshot at execution time;
5. the existing M14 execution, retry, persistence, and aggregate-state semantics remain unchanged.

## Accepted Decisions

### 1. Scheduler Remains a Trigger Mechanism

The scheduler owns timing only.

It must not:

- enumerate stocks;
- calculate analysis inputs;
- decide which symbols to execute;
- rank opportunities;
- persist analytical results;
- implement retry policy.

### 2. Dedicated Configured-Market Trigger

Introduce an application capability named:

`ScheduledConfiguredMarketAnalysis`

Its responsibility is to register `RunConfiguredMarketAnalysis` as a scheduler operation for a requested `run_at` timestamp.

When the scheduled operation actually runs, it invokes the configured-market capability with the execution date determined at invocation time.

### 3. Execution Date Semantics

The scheduled operation uses the current calendar date at execution time rather than registration time.

This prevents a schedule created before midnight from accidentally attributing the later execution to the previous calendar date.

Timezone/calendar policy is not introduced in M18. The application uses the runtime's existing date semantics.

### 4. One-Shot Scheduling Only

M18 supports one scheduled execution.

Recurring schedules, cron expressions, EGX trading-calendar awareness, market-close calculation, missed-run recovery, persistence, and distributed scheduling remain separate future design gates.

### 5. Universe Snapshot Timing

The configured universe is resolved when the scheduled operation executes, not when the schedule is registered.

This keeps scheduling independent from the market universe and ensures the run uses the current configured catalog at execution time.

### 6. Failure Semantics

Scheduler execution does not reinterpret market-analysis failures.

`RunConfiguredMarketAnalysis` and `RunMarketAnalysis` remain responsible for aggregate execution semantics.

If the scheduled operation raises an unexpected infrastructure/application exception before an execution result exists, the scheduler propagates that exception according to its existing one-shot behavior.

### 7. No New Persistence

M18 introduces no schedule persistence and no execution-history schema.

Successful stock results continue through the existing `AnalysisResultStore` boundary.

### 8. No API Expansion

M18 does not add a scheduling API.

The existing command endpoint remains an immediate trigger. A future scheduling API requires a separate contract covering authorization, schedule identity, validation, persistence, and lifecycle.

### 9. Sequential Execution Remains

The scheduled trigger does not change M14/M17 execution strategy. Configured-market analysis remains sequential.

## Application Boundary

```
Scheduler
    ↓
ScheduledConfiguredMarketAnalysis
    ↓
RunConfiguredMarketAnalysis
    ↓
StockCatalog.symbols()
    ↓
RunMarketAnalysis
    ↓
RunStockAnalysis
    ↓
AnalysisResultStore
```

## TDD Acceptance Criteria

- scheduling registers exactly one callable operation;
- the operation does not execute during registration;
- when due, the operation invokes `RunConfiguredMarketAnalysis`;
- the configured-market capability receives the execution date at run time;
- a schedule captures no universe snapshot during registration;
- scheduler pending work is removed when the operation becomes due under the existing scheduler contract;
- configured-market execution semantics remain unchanged;
- no recurring scheduling behavior is introduced;
- no schedule persistence is introduced.

## Non-Goals

M18 does not introduce:

- recurring schedules;
- cron;
- EGX trading calendar;
- market-close calculation;
- persistent schedules;
- missed-run recovery;
- distributed workers;
- concurrency;
- scheduling API;
- authentication/authorization;
- notification delivery;
- ranking changes;
- dashboard changes;
- portfolio allocation;
- trading execution;
- AI-based scheduling or stock selection.

## Design Gate Decision

**Status: Accepted — implementation is authorized for the M18 MVP defined here.**

M18 is a thin scheduling adapter around the already accepted configured-market execution capability. It must not move business logic into the scheduler.

## Revisit Conditions

Revisit this design when the system needs recurring schedules, trading-calendar semantics, durable schedules, multiple schedule types, missed-run recovery, distributed execution, or user-managed scheduling.
