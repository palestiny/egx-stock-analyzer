# DEC-124 — M60 Production Maintenance Scheduling Design Gate

**Status:** Accepted — Windows Task Scheduler deployment mapping
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

## 9. Accepted Decisions

### 9.1 Deployment Target

**Windows host + Windows Task Scheduler** is the current production deployment mapping.

This is a deployment choice, not an application architecture dependency. The application remains scheduler-agnostic and the maintenance command remains the stable application boundary.

A future container or managed-service deployment may introduce a different scheduler mapping without changing M58/M59 policy semantics.

### 9.2 Invocation Frequency

Run automatic retention **once per day at 03:30 local host time**.

Daily execution matches the age-based retention policy while avoiding unnecessary repeated maintenance work. Retention eligibility remains owned by M58; the schedule does not redefine the 30-day policy.

### 9.3 Overlap Policy

**Do not start a new invocation while a previous invocation is still running.**

Windows Task Scheduler must use the equivalent of an `IgnoreNew` overlap policy.

### 9.4 Timeout

The scheduled task has a **30-minute execution ceiling**.

This is an operational safety bound and does not change the M58/M57 batch limit or lifecycle eligibility rules.

### 9.5 Scheduler Retry

A failed invocation may be retried **up to 3 times**, with a **10-minute delay** between attempts.

Retries remain scheduler-level retries of the same bounded maintenance command.

### 9.6 Observability

The MVP uses:

- process exit code as the scheduler success/failure signal;
- Windows Task Scheduler operational history;
- command stdout/stderr captured by the deployment wrapper;
- existing M57/M58 audit records as the application-level destructive-operation record.

No new application telemetry subsystem is introduced by M60.

### 9.7 Configuration and Secrets

The scheduler supplies no secrets directly.

The task runs under the deployment service account and reads normal application configuration/environment. The SQLite database path is provided through the existing command/configuration boundary; no credentials are embedded in task XML or scripts.

### 9.8 Dry Run

Dry-run remains **operator-only** and is not scheduled.

### 9.9 Scheduler Execution History

Task Scheduler history is sufficient for the M60 MVP. Durable application-level scheduler occurrence history is deferred.

## 10. Deployment Mapping

The repository will contain a Windows deployment wrapper and registration/removal scripts under `deploy/windows/`.

The wrapper will:

1. locate the configured Python executable;
2. invoke `python -m app.infrastructure.maintenance.automatic_retention_command`;
3. preserve the command exit code;
4. capture command output to a deployment-owned log location;
5. never implement retention or deletion logic itself.

The registration script will configure the daily trigger, non-overlap behavior, timeout, and retry policy. It will not embed secrets or retention policy values.

## 11. Verification Shape

The deployment mapping must verify:

- disabled retention exits successfully and performs no deletion;
- normal enabled invocation returns the maintenance command exit code;
- command failure is visible as task failure;
- timeout terminates the task according to the operational ceiling;
- overlapping invocations are rejected/ignored;
- scheduler retry is bounded to the accepted retry count;
- missing configuration fails without creating a destructive path;
- dry-run remains unscheduled;
- M57/M58 invariants remain unchanged.

## 12. Decision Gate

**Status: Accepted — implementation is authorized for the Windows Task Scheduler deployment mapping defined above.**

The scheduler owns only timing, process execution, timeout, retry, and operational observation.

M59 remains the only application command boundary; M58 remains the retention policy boundary; M57 remains the physical purge boundary.

No application background scheduler, generic scheduler abstraction, or second destructive path is authorized by this gate.
