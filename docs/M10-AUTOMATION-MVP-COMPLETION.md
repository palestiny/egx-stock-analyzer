# M10 — Automation MVP Completion

## Status
Completed — MVP

## Scope Completed

M10 establishes an application-level automation path around the existing analysis domain.

### Execution

- one Execution represents the complete daily market analysis
- stock results are processed independently
- partial failures produce `COMPLETED_WITH_ERRORS`
- all failures produce `FAILED`
- transient failures may retry according to `RetryPolicy`
- idempotency prevents duplicate active/completed executions
- failed and completed-with-errors executions may be recovered with a new execution

### Analysis Integration

The execution flow invokes the existing stock-analysis pipeline without moving business rules into the execution model.

### Triggers

- manual trigger supported
- scheduled trigger supported

### Scheduler

- explicit `run_at` timing
- in-process scheduler
- one-shot operations
- due operations execute through `run_due(now)`
- future operations remain pending

### Daily Scheduling Use Case

`DailyAnalysisSchedule` provides the application boundary for registering the daily analysis with a requested `run_at`.

The caller supplies `run_at`; market-calendar calculation is intentionally outside M10.

## Architectural Boundary

```text
Trigger / Schedule Registration
            ↓
Scheduler (WHEN)
            ↓
DailyMarketAnalysis (WHAT)
            ↓
Execution
            ↓
Existing Analysis Pipeline
```

Automation orchestrates existing business capabilities. It does not redefine analysis rules.

## Explicitly Deferred

- recurring schedules
- cron expressions
- EGX trading calendar
- market-close calculation
- persistent schedules
- restart recovery
- distributed workers/queues
- Celery/Redis/RabbitMQ/Kubernetes
- advanced concurrency/scaling
- scheduler monitoring/dashboard

These require separate design decisions.

## Verification

M10 was built through TDD slices covering execution lifecycle, partial failure, retry, idempotency, analysis integration, manual trigger, scheduled trigger, scheduler timing, daily scheduling, and real scheduler integration.
