# DEC-078 — M19 Recurring Market Scheduling Design Gate

**Status:** Accepted  
**Date:** 2026-09-18  
**Milestone:** M19 — Recurring Market Scheduling

## Context

M18 established a one-shot scheduling adapter around the accepted configured-market execution capability:

```
Scheduler
    ↓
ScheduledConfiguredMarketAnalysis
    ↓
RunConfiguredMarketAnalysis
    ↓
RunMarketAnalysis
```

The current scheduler can register a callable for a specific timestamp and consume it once when due. M18 deliberately deferred recurring schedules, EGX trading-calendar semantics, missed-run recovery, schedule persistence, and user-managed scheduling.

The project now has the application capability required to execute the configured EGX universe. The next design question is how recurring execution should be represented without moving business logic into the scheduler.

## Problem

A production-oriented market analyzer needs a repeatable way to request market-wide analysis on a defined cadence.

A recurring schedule introduces questions that a one-shot timestamp does not answer:

- What constitutes a valid recurrence?
- Which timezone defines the schedule?
- Should execution be based on calendar days or EGX trading days?
- What happens on weekends and market holidays?
- Does a missed occurrence execute later?
- Who owns recurrence calculation?
- Should schedule state survive process restart?
- How are duplicate executions prevented?
- Does the scheduler own recurrence, or does an application scheduling capability?
- What should happen when one scheduled execution is still running when the next occurrence becomes due?

These decisions affect correctness and operational behavior and should be explicit before implementation.

## Desired Outcome

Define a recurring scheduling capability that can:

1. represent an explicit recurring market-analysis schedule;
2. calculate the next intended execution without embedding market-analysis business logic in the scheduler;
3. use an explicit timezone/calendar policy;
4. avoid accidental duplicate execution;
5. define missed-run behavior;
6. preserve the existing `RunConfiguredMarketAnalysis` semantics;
7. remain testable without wall-clock dependence;
8. leave durable schedule persistence as a separate concern unless the accepted design explicitly requires it.

## Scope

### In scope

- recurrence representation;
- schedule ownership;
- timezone semantics;
- trading-day/calendar boundary;
- next-run calculation;
- missed-run behavior;
- overlap/concurrency semantics;
- interaction with `Scheduler`;
- interaction with `RunConfiguredMarketAnalysis`;
- idempotency expectations;
- deterministic tests.

### Explicitly out of scope

- user-facing scheduling API;
- authentication/authorization;
- notification delivery;
- ranking changes;
- dashboard redesign;
- trading execution;
- portfolio allocation;
- AI-based scheduling;
- distributed scheduler infrastructure;
- multi-process coordination;
- persistent schedule storage unless separately accepted;
- changing stock-analysis or market-analysis rules.

## Alternatives Considered

### A — Put recurrence inside `Scheduler`

The scheduler would accept recurrence rules and calculate future occurrences.

**Trade-offs:**

- centralized timing behavior;
- but couples generic scheduling infrastructure to recurrence policy;
- risks turning the scheduler into a business-policy owner;
- harder to reuse for different scheduling domains.

### B — Dedicated recurring application capability

Introduce a capability that owns recurring market-analysis policy and uses the scheduler as a timing mechanism.

Conceptually:

```
RecurringConfiguredMarketAnalysis
          ↓
Scheduler
          ↓
RunConfiguredMarketAnalysis
```

**Trade-offs:**

- keeps market-analysis scheduling semantics explicit;
- keeps generic scheduler timing-focused;
- adds one application component;
- requires clear responsibility for next-run calculation.

### C — External cron only

Use an operating-system or deployment scheduler to invoke market analysis repeatedly.

**Trade-offs:**

- low application complexity;
- but recurrence policy moves outside the application;
- harder to test and represent consistently;
- missed-run and duplicate-run behavior become deployment concerns.

## Open Questions

1. **Recurrence model:** fixed interval, daily time-of-day, or a small explicit recurrence model?
2. **Timezone:** which timezone is authoritative for schedule evaluation?
3. **Trading calendar:** should M19 use weekdays only, or an explicit EGX trading calendar abstraction?
4. **Missed runs:** skip missed occurrences, execute the latest missed occurrence, or catch up all occurrences?
5. **Overlap:** what happens if a new occurrence becomes due while the previous execution is still running?
6. **Idempotency:** what identity defines one scheduled occurrence?
7. **Persistence:** should schedules survive restart in M19, or remain process-local?
8. **Ownership:** should next-run calculation live in the recurring application capability while `Scheduler` remains timestamp-based?
9. **Clock:** should time be injected as a clock abstraction for deterministic tests?
10. **Failure handling:** after a scheduled execution fails, should the recurrence continue according to the schedule?

## Proposed Invariants

1. The scheduler remains responsible for timing mechanics, not market-analysis policy.
2. Recurring scheduling must not duplicate `RunConfiguredMarketAnalysis` logic.
3. Each intended occurrence has a deterministic identity.
4. Missed-run behavior is explicit rather than accidental.
5. The configured universe remains resolved at execution time.
6. Recurrence calculations are deterministic under an injected clock/calendar policy.
7. A failed occurrence must not silently disable future occurrences unless the accepted policy explicitly says so.
8. M19 does not change stock-level analytical semantics.
9. No concurrency is introduced without an explicit overlap decision.
10. Persistence is not implied merely because recurrence exists.

## TDD Acceptance Shape

Before implementation, tests should establish at least:

- recurrence produces the expected next occurrence;
- timezone conversion is deterministic;
- non-trading dates follow the accepted calendar policy;
- missed occurrences follow the accepted policy;
- occurrence identity is deterministic;
- duplicate occurrence execution is prevented according to the accepted idempotency contract;
- overlap behavior follows the accepted policy;
- a failed occurrence does not unexpectedly stop future scheduling;
- registration does not execute analysis immediately;
- due execution delegates to `RunConfiguredMarketAnalysis`;
- configured universe is resolved at execution time;
- scheduler remains unaware of market-analysis rules.


## Accepted Decisions

1. **Recurrence:** M19 supports one explicit recurrence shape: daily at a configured local time. Fixed intervals, cron expressions, and multiple recurrence rule types are deferred.

2. **Timezone:** the schedule timezone is explicit and defaults to Africa/Cairo. Schedule evaluation uses timezone-aware datetimes; naive schedule timestamps are rejected.

3. **Trading calendar:** M19 uses Monday through Friday as eligible days. This is not an authoritative EGX holiday calendar; official EGX holiday/session semantics require a future trading-calendar design.

4. **Missed runs:** missed occurrences are skipped. On wake-up after missed times, the capability calculates the next future occurrence instead of replaying historical occurrences.

5. **Overlap:** M19 does not introduce concurrent market-analysis execution. Only one occurrence may be active; a due occurrence is skipped if another occurrence is already running.

6. **Occurrence identity/idempotency:** an occurrence is identified by recurring schedule identity plus scheduled local date and time. Consumed occurrence identities are tracked in process-local state. Durable idempotency is deferred with persistence.

7. **Persistence:** schedules are process-local. No schedule persistence or restart recovery is introduced; a restart requires registration again.

8. **Ownership:** RecurringConfiguredMarketAnalysis owns recurrence policy and next-occurrence calculation. Scheduler remains a generic timestamp-based timing mechanism. RunConfiguredMarketAnalysis remains the business-execution capability.

9. **Clock:** time is accessed through an injected clock abstraction so recurrence and timezone calculations are deterministic in tests.

10. **Failure:** a failed occurrence does not disable future occurrences. Existing market-analysis retry/failure semantics remain unchanged.

## Design Gate Decision

**Status: Accepted — implementation is authorized for the M19 MVP defined here.**

Accepted boundary:

RecurringConfiguredMarketAnalysis → Scheduler → RunConfiguredMarketAnalysis → StockCatalog.symbols() → RunMarketAnalysis → RunStockAnalysis → AnalysisResultStore

The recurring capability owns schedule semantics only. The scheduler owns timing mechanics only. Market-analysis capabilities own market execution only.

## TDD Acceptance Criteria

- daily recurrence calculates the expected next occurrence;
- timezone conversion is deterministic;
- weekdays are accepted and weekend dates are skipped;
- missed occurrences are skipped rather than replayed;
- occurrence identity is deterministic;
- duplicate occurrence execution is prevented in-process;
- overlapping execution is not started concurrently;
- failed occurrences do not disable future occurrences;
- registration does not execute analysis immediately;
- due execution delegates to RunConfiguredMarketAnalysis;
- the configured universe is resolved at execution time;
- the scheduler remains unaware of market-analysis rules.

## Design Gate Rule

M19 implementation is not authorized until the open questions above are resolved and the accepted decisions are recorded in this document and the project Decision Log.

## Revisit Conditions

Revisit this gate if the system later requires durable user-managed schedules, multiple independent schedule types, distributed scheduling, multi-process coordination, or a full EGX trading-calendar service.
