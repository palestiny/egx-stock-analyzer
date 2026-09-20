# M10 Scheduler MVP Completion

## Status

Completed.

## Scope

The M10 scheduler MVP provides an in-process scheduling boundary for one-shot analysis operations.

The scheduler contract is:

```text
schedule(operation, run_at)
        ↓
   pending operation
        ↓
   run_due(now)
        ↓
 execute operations where run_at <= now
```

## Decisions Implemented

- Scheduler is an application boundary.
- `Scheduler` is a Protocol.
- `InProcessScheduler` is the MVP implementation.
- Scheduling is one-shot.
- `run_at` is explicit and timezone-aware at the caller boundary.
- Operations execute only when their scheduled time is due.
- Due operations are removed before execution, so a completed scheduled operation is not executed again by a later `run_due()` call.
- Persistent scheduling, recurring/cron scheduling, distributed workers, queues, and external scheduler infrastructure remain deferred.

## Scheduled Trigger Integration

`ScheduledAnalysisTrigger` now accepts both analysis inputs and `run_at`, then registers the analysis operation with the scheduler.

The trigger still does not own scheduling mechanics. It defines WHAT should execute; `InProcessScheduler` defines WHEN it executes.

## TDD Coverage

- scheduler registers an operation
- due operation executes
- operation does not execute before its due time
- scheduled trigger passes the scheduled time to the scheduler
- scheduled trigger executes the analysis when the in-process scheduler reaches the due time

## Architectural Boundary

```text
Scheduler
   │ WHEN
   ▼
ScheduledAnalysisTrigger
   │ WHAT
   ▼
DailyMarketAnalysis
   ▼
Execution
```

The business analysis pipeline remains independent from scheduling technology.

## Deferred

- recurring schedules
- cron expressions
- persistent schedules
- scheduler recovery after process restart
- distributed scheduling
- queues/workers
- concurrency and scaling
- monitoring/dashboard integration

## Next M10 Step

Define the application-level scheduling use case that determines which daily analysis should be scheduled and at what business time. This should be a separate design decision from the scheduler mechanics.
