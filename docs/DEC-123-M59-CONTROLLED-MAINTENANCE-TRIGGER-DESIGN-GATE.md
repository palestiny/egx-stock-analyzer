# DEC-123 — M59 Controlled Maintenance Trigger Design Gate

**Status:** Proposed — Decision Required  
**Date:** 2026-09-21  
**Milestone:** M59 — Controlled Maintenance Trigger

## 1. Problem

M58 implemented automatic analysis retention but intentionally stopped at the application capability boundary. The capability is configured and composed in the runtime, but no production trigger was introduced.

The repository already contains a scheduler abstraction, recurring scheduling policy, durable scheduled-workflow execution, and startup recovery. The current runtime does not expose a general production maintenance trigger for automatic retention.

The M59 question is therefore:

> **What component owns the production trigger that invokes controlled maintenance capabilities such as automatic retention?**

## 2. Current State

Relevant mechanisms:
- `app/application/execution/scheduler.py`: `Scheduler` protocol and in-memory `InProcessScheduler`.
- `app/application/execution/recurring_configured_market_analysis.py`: recurring weekday scheduling policy delegating timing to `Scheduler`.
- `RunDurableScheduledWorkflow`: durable occurrence identity, idempotency, persisted execution state, failure handling, and recovery.
- `AutomaticWorkflowRecovery`: startup recovery of interrupted scheduled workflow executions.
- M58 `AutomaticAnalysisRetention`: configured in runtime, disabled by default, delegates destructive work to M57, and is not invoked at startup.

Boundary:

    Trigger / Maintenance Driver
              ↓
    AutomaticAnalysisRetention
              ↓
    PurgeAnalysisLifecycle (M57)
              ↓
    SQLite lifecycle transaction

No current production maintenance driver exists for the first box.

## 3. Goals

1. Invoke automatic retention only when explicitly enabled.
2. Preserve M57 as the physical-purge authority.
3. Be safe across restart and repeated invocation.
4. Remain bounded and observable.
5. Keep ordinary API startup free of destructive maintenance.
6. Allow future controlled maintenance capabilities without coupling them to analysis logic.
7. Keep deployment timing outside domain policy.

## 4. Non-Goals

- changing M56 logical deletion;
- changing M57 purge semantics;
- changing M58 retention policy;
- adding another deletion path;
- introducing distributed scheduling;
- redesigning scheduled market analysis;
- changing authorization roles;
- adding a background worker merely for convenience.

## 5. Gaps

`InProcessScheduler` is an application-level in-memory queue; it does not provide durable timer state, process lifetime management, deployment restart behavior, or an OS/container trigger.

The durable scheduled-workflow model provides strong persistence and recovery semantics, but it is currently shaped around scheduled market analysis. Reusing it for maintenance would introduce coupling that needs explicit justification.

Startup recovery already exists, but M58 explicitly excludes automatic retention from startup. Startup must not become a destructive-maintenance trigger.

## 6. Alternatives

### A — External scheduler invokes a maintenance command

    OS / container scheduler → maintenance command → AutomaticAnalysisRetention → M57 purge

Advantages: smallest runtime surface, deployment-owned timing, no FastAPI background worker, restart does not implicitly trigger deletion.

Trade-offs: deployment-specific scheduler configuration, missed invocations depend on operations, command lifecycle/observability must be defined.

### B — Application-owned background scheduler

    FastAPI process → background maintenance loop → AutomaticAnalysisRetention

Advantages: self-contained deployment and no external scheduler configuration.

Trade-offs: lifecycle/shutdown/concurrency concerns, duplicate execution across instances, stronger coupling to API process lifetime.

### C — Reuse the durable scheduled-workflow model

    maintenance occurrence → durable execution → AutomaticAnalysisRetention → M57 purge

Advantages: durable history, existing idempotency/recovery patterns, strong observability.

Trade-offs: couples maintenance to market-analysis workflow concepts and requires maintenance-specific occurrence/recovery semantics.

### D — Generic maintenance runner with external trigger

    External scheduler → generic maintenance runner → maintenance capabilities

Advantages: deployment-owned timing plus a reusable application boundary for future maintenance capabilities.

Trade-offs: adds a new abstraction and requires common failure/order/idempotency/observability semantics; may be unnecessary if retention remains the only maintenance task.

## 7. Engineering Assessment

The evidence favors evaluating **A** first because it adds the smallest runtime surface and keeps deployment timing separate from business capabilities.

**D** becomes more attractive if several independent maintenance capabilities are expected soon.

**B** should not be introduced merely for convenience because it changes process-lifecycle and multi-instance behavior.

**C** should only be selected if maintenance genuinely needs the same durable execution model as scheduled analysis; infrastructure reuse alone is not sufficient justification.

This is an engineering assessment, not the owner decision.

## 8. Decision Criteria

- restart behavior;
- duplicate invocation behavior;
- multi-instance deployment behavior;
- missed-run behavior;
- observability/auditability;
- operational configuration burden;
- coupling to FastAPI lifecycle;
- reuse for future maintenance;
- implementation footprint;
- failure/retry semantics.

## 9. Required Invariants

Whichever option is selected:

1. disabled M58 retention cannot delete data;
2. the trigger cannot bypass M58 policy validation;
3. physical deletion still occurs only through M57;
4. repeated trigger delivery is safe;
5. failed maintenance is observable;
6. ordinary application startup does not trigger retention;
7. execution remains bounded;
8. visible or active analysis data cannot become eligible through the trigger;
9. deployment timing does not redefine retention policy;
10. the trigger does not redefine retention eligibility.

## 10. TDD Shape After Decision

- enabled/disabled behavior;
- invocation contract;
- repeated invocation;
- failure handling;
- restart behavior;
- missed occurrences if applicable;
- concurrent/duplicate triggers;
- batch bound preservation;
- audit identity preservation;
- no-startup-trigger invariant;
- reuse of `AutomaticAnalysisRetention`;
- unchanged M57 behavior.

## 11. Decision Gate

**Status: Proposed — owner decision required.**

No implementation is authorized by this document.

The owner should select A/B/C/D or define another alternative, with trade-offs recorded before implementation.

## 12. Next Step

After decision: update this gate → define exact trigger contract → update roadmap/current state → TDD RED → implement → review/refactor → CI/verification → close M59.
