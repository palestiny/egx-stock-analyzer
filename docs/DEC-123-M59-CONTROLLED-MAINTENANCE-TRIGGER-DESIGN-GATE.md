# DEC-123 — M59 Controlled Maintenance Trigger Design Gate

**Status:** Accepted — Option A  
**Date:** 2026-09-21  
**Milestone:** M59 — Controlled Maintenance Trigger

## 1. Problem

M58 implemented automatic analysis retention but intentionally stopped at the application capability boundary. The capability is configured and composed in the runtime, but no production trigger was introduced.

The M59 question was:

> **What component owns the production trigger that invokes controlled maintenance capabilities such as automatic retention?**

## 2. Decision

**Accepted option: A — External scheduler invokes a maintenance command.**

The production flow is:

    OS / container scheduler
              ↓
    maintenance command
              ↓
    AutomaticAnalysisRetention
              ↓
    PurgeAnalysisLifecycle (M57)
              ↓
    SQLite lifecycle transaction

The application owns the maintenance capability and its safety/policy semantics. The deployment environment owns when the command is invoked.

## 3. Why A

A provides the smallest runtime surface while keeping deployment timing separate from retention policy.

It avoids:
- coupling maintenance to FastAPI process lifetime;
- introducing an application background worker;
- multi-instance duplicate scheduler ownership;
- coupling retention to the durable scheduled-market-analysis workflow model;
- introducing a generic maintenance abstraction before multiple maintenance capabilities justify it.

Option D remains a possible future evolution if multiple independent maintenance capabilities require a common application-level maintenance runner. That future possibility does not justify adding the abstraction in M59.

## 4. Explicit Trade-offs Accepted

The project accepts these trade-offs for M59:

- scheduler configuration is deployment-specific;
- a missed scheduled invocation is an operational concern rather than an application scheduling concern;
- command execution and failure must be observable;
- the command must have an explicit lifecycle/exit contract;
- deployment scheduling must not redefine retention eligibility or policy;
- external scheduling does not provide durable occurrence history by itself.

## 5. Scope

M59 will implement only the application-side maintenance command contract required to invoke M58 safely.

In scope:
- explicit maintenance command entrypoint;
- invocation of `AutomaticAnalysisRetention`;
- dry-run support where exposed by M58;
- bounded execution through the existing M58/M57 controls;
- clear success/disabled/failure outcome and process exit semantics;
- tests for invocation, disabled behavior, failures, repeated execution, and safety invariants;
- documentation of the deployment-trigger boundary.

Out of scope:
- OS/container scheduler configuration;
- a new application background scheduler;
- a distributed scheduler;
- a generic maintenance runner;
- changes to M56 logical deletion;
- changes to M57 purge semantics;
- changes to M58 retention eligibility/policy.

## 6. Required Invariants

1. Disabled M58 retention cannot delete data.
2. The command cannot bypass M58 policy validation.
3. Physical deletion still occurs only through M57.
4. Repeated command invocation is safe.
5. Failed maintenance is observable through command outcome/exit status.
6. Ordinary application startup does not trigger retention.
7. Execution remains bounded by the existing retention batch limit.
8. Visible or active analysis data cannot become eligible through the command.
9. Deployment timing does not redefine retention policy.
10. The command does not redefine retention eligibility.
11. No second destructive deletion path is introduced.

## 7. Command Contract to Define

Before implementation, the command must have explicit semantics for:

- normal execution;
- disabled retention;
- dry-run/preview;
- invalid configuration;
- runtime failure;
- empty candidate set;
- repeated invocation;
- process exit status;
- operator-visible summary.

The command must invoke the existing `AutomaticAnalysisRetention` capability rather than reproducing its logic.

## 8. TDD Shape

The implementation test suite must cover:

- enabled execution;
- disabled execution;
- dry-run;
- invalid configuration;
- no candidates;
- candidate batch bound;
- repeated invocation;
- failure propagation/observability;
- audit operation identity;
- no-startup-trigger invariant;
- reuse of `AutomaticAnalysisRetention`;
- unchanged M57 behavior.

## 9. Decision Gate

**Status: Accepted — implementation authorized for M59 within the scope above.**

Owner decision: **Option A — External scheduler → maintenance command → M58 retention capability.**

No OS/container scheduler is configured by this repository change unless a later explicit deployment task requires it.

## 10. Next Step

Define the exact command contract and locate the repository's existing CLI/entrypoint conventions. Then:

**TDD RED → implement → review/refactor → CI/verification → documentation closeout → M59 completion.**