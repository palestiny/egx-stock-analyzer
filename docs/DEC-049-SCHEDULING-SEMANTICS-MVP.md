# DEC-049 — Scheduling Semantics MVP

## Status
Accepted

## Context
M10 needs a concrete scheduling contract while keeping scheduling technology separate from analysis orchestration.

The scheduler must answer **when** an already-defined operation should run. It must not own market analysis or business rules.

## Decision
For the M10 MVP, scheduling is **one-shot execution at a specific timezone-aware `datetime`**.

Conceptually:

```text
schedule(operation, run_at)
        ↓
Scheduler waits until run_at
        ↓
operation()
```

The scheduler remains an in-process implementation. It is live only while the application process is running.

## Why
- Explicit timing semantics are testable.
- One-shot scheduling is the smallest useful primitive.
- Daily recurring analysis can be built later as a higher-level scheduling policy without changing `DailyMarketAnalysis`.
- Avoids introducing cron expressions, recurrence rules, persistence, or external infrastructure into the MVP.

## Trade-offs
### Alternative: recurring/cron scheduler now
Would model the eventual daily use case directly, but introduces recurrence semantics and configuration before the one-shot primitive is proven.

### Alternative: delay/interval based scheduling
Simpler in some implementations, but less explicit and harder to reproduce because the meaning depends on when scheduling occurred.

### Alternative: external scheduler
Provides persistence and process independence, but adds infrastructure and operational complexity outside the M10 MVP.

## Boundaries
Scheduler owns:
- waiting for the requested time
- executing the registered operation

Scheduler does not own:
- market analysis
- execution business state
- retry policy
- data acquisition
- reporting
- alerts
- persistence
- distributed execution
- recurrence policy

## Deferred
- daily recurring schedules
- cron expressions
- persistent schedules
- missed-run policy
- timezone/calendar policy beyond requiring a timezone-aware `datetime`
- distributed scheduling
- scheduler persistence and monitoring
