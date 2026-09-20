# DEC-051 — Daily Schedule Time Ownership

## Status
Accepted — MVP

## Decision

For the M10 MVP, `run_at` is supplied by the caller of `DailyAnalysisSchedule.register()`.

`DailyAnalysisSchedule` does not calculate the daily execution time.

## Rationale

Calculating a real daily market-analysis time requires business/calendar semantics that are outside the current scheduling boundary, such as:

- EGX trading sessions
- trading days and holidays
- timezone policy
- market-close semantics
- future recurring schedule rules

Adding those rules now would mix scheduling infrastructure with market-calendar business logic before that domain has been explicitly designed.

## Ownership

```text
Caller / future Calendar Policy
            │
            │ run_at
            ▼
DailyAnalysisSchedule
            │
            ▼
ScheduledAnalysisTrigger
            │
            ▼
InProcessScheduler
```

The scheduler owns **WHEN to execute a registered operation**.

A future market-calendar/schedule policy may own **HOW run_at is calculated**.

## Deferred

- EGX trading calendar
- market-close calculation
- holidays/weekends
- recurring daily schedules
- cron expressions
- persistent schedules
- timezone conversion policy

These require a separate Design Gate and must not be introduced implicitly into M10.

## Consequence

M10 remains a small, deterministic scheduling boundary and does not acquire hidden market-calendar responsibilities.
