# DEC-050 — Daily Analysis Schedule MVP

## Status
Accepted — MVP

## Context

M10 already has:

- `DailyMarketAnalysis` owning WHAT happens during a market analysis execution.
- `ScheduledAnalysisTrigger` connecting analysis to scheduling.
- `InProcessScheduler` owning WHEN an operation becomes due.

The remaining application boundary is a small use case for registering the daily market analysis with a requested execution time.

## Decision

Introduce `DailyAnalysisSchedule` as an application-level use case.

Its responsibility is only to register the existing scheduled trigger with:

- the stock-analysis inputs
- the requested `run_at` timestamp

It does not:

- perform analysis
- calculate the schedule time
- own scheduler technology
- create executions directly
- implement business rules
- persist schedules
- implement recurring/cron behavior

## Flow

```text
DailyAnalysisSchedule
        ↓
ScheduledAnalysisTrigger
        ↓
Scheduler
        ↓
DailyMarketAnalysis
        ↓
Execution
```

## Timing Ownership

The caller provides `run_at` for this MVP.

The scheduling use case does not decide whether the analysis should run at 12:00, 15:00, or any other time. Calendar/session-aware scheduling remains outside this use case.

## TDD Contract

```text
register(inputs, run_at)
        ↓
trigger.schedule(inputs, run_at)
```

The use case returns `None`; registration is the responsibility of the trigger/scheduler boundary.

## Deferred

- recurring schedules
- cron expressions
- EGX trading-calendar calculation
- persistent schedules
- scheduler recovery after process restart
- distributed scheduling
- timezone policy beyond the supplied timezone-aware timestamp
- dynamic schedule management

## Consequence

The application layer now has an explicit boundary for registering the daily analysis without coupling business analysis to scheduling technology.
