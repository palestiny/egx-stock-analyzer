# DEC-124 — M60 Production Maintenance Scheduling Design Gate

**Status:** Proposed
**Date:** 2026-09-22
**Milestone:** M60 — Production Maintenance Scheduling

## 1. Problem

M59 established a controlled application-side maintenance command for automatic analysis retention, but deliberately left invocation timing to the deployment environment.

The next question is whether and how the project should configure a production scheduler to invoke that command reliably.

## 2. Intended Outcome

Define a deployment-side trigger contract that can invoke the existing M59 maintenance command without moving retention policy, eligibility, purge semantics, or destructive behavior into the scheduler.

## 3. In Scope

- scheduler ownership and deployment boundary;
- invocation frequency;
- overlap/concurrency policy;
- failure/retry behavior at the scheduler boundary;
- timeout expectations;
- observability requirements;
- configuration/secrets boundary;
- safe behavior when automatic retention is disabled;
- documentation of the selected deployment mechanism.

## 4. Out of Scope

- changing M57 physical purge semantics;
- changing M58 retention policy or eligibility;
- changing M59 command behavior except where an explicit deployment contract requires it;
- introducing an application background worker;
- distributed job orchestration;
- generic scheduler abstraction;
- unrelated market-analysis scheduling.

## 5. Candidate Options

### Option A — OS-level scheduler

The host invokes the command directly on a fixed schedule.

**Trade-offs:** simple and low application coupling; deployment-specific and requires host-level operational management.

### Option B — Container/orchestrator scheduler

The deployment platform invokes a short-lived maintenance container/job.

**Trade-offs:** better fit for containerized deployments and ephemeral execution; requires a deployment platform capable of scheduled jobs and introduces platform-specific configuration.

### Option C — Application background scheduler

The running application owns the schedule.

**Trade-offs:** centralized application control; increases lifecycle coupling and creates multi-instance coordination concerns. This conflicts with the M59 accepted boundary unless a later decision explicitly changes it.

### Option D — External managed scheduler

A managed scheduling service invokes the maintenance command through an explicit deployment integration.

**Trade-offs:** can reduce host/platform scheduling responsibility; adds external infrastructure, credentials, and operational dependencies.

## 6. Required Decisions

Before implementation, resolve:

1. deployment target (Windows host, Linux host, container platform, or managed service);
2. invocation frequency;
3. overlap behavior if one invocation is still running;
4. timeout;
5. scheduler-level retry policy;
6. observability and alerting;
7. credential/configuration delivery;
8. whether dry-run should have an operational schedule or remain operator-only;
9. whether scheduler execution history is required.

## 7. Invariants

1. The scheduler never calculates retention eligibility.
2. The scheduler never performs physical deletion directly.
3. M59 remains the only application command boundary.
4. M57 remains the only physical purge capability.
5. Disabled retention remains non-destructive.
6. Scheduler retries must not create a second destructive path.
7. One invocation must remain bounded by M58/M57 limits.
8. Overlap must not cause unsafe concurrent lifecycle mutation.

## 8. TDD / Verification Shape

The design must establish tests or deployment-level verification for:

- disabled retention;
- normal invocation;
- command failure;
- timeout;
- repeated invocation;
- overlap;
- retry;
- configuration/credential failure;
- scheduler observability;
- preservation of M57/M58 invariants.

## 9. Decision Gate

**Status: Proposed — implementation is not authorized until the deployment target and scheduling semantics are explicitly accepted.**

No scheduler configuration should be added to the repository until this gate is accepted.
