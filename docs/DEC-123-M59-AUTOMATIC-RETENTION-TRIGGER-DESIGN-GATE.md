# DEC-123 — M59 Automatic Retention Trigger Design Gate

**Status:** Proposed  
**Date:** 2026-09-22  
**Milestone:** M59

## Purpose

M58 implemented and composed the automatic-retention policy, but intentionally stopped before selecting the concrete controlled trigger mechanism.

M59 defines that trigger boundary without changing retention policy, deletion semantics, authorization, or the M57 physical-purge capability.

## Problem

Automatic retention is currently:

- disabled by default;
- safe to invoke explicitly through its application capability;
- not invoked during application startup;
- intended to be maintenance/scheduler-driven.

The system therefore needs an explicit trigger mechanism before automatic retention can become an operationally usable scheduled capability.

## Scope

M59 covers:

- trigger ownership;
- scheduler/maintenance boundary;
- invocation frequency contract;
- enablement/configuration interaction;
- overlap/concurrency protection;
- failure and retry semantics at the trigger boundary;
- observability/audit expectations;
- deterministic testing.

## Out of Scope

- changing the 30-day retention policy;
- changing M57 physical purge semantics;
- new deletion semantics;
- new authorization roles;
- distributed scheduling;
- high-availability leader election;
- external job queues;
- dashboard controls;
- user-configurable retention;
- changing startup behavior into destructive maintenance.

## Existing Boundary

```
Trigger
   ↓
AutomaticRetentionPolicy
   ↓
M57 PhysicalPurge
   ↓
SQLite lifecycle transaction
   ↓
Management Audit
```

The trigger must invoke the accepted M58 application capability. It must not perform persistence deletion directly.

## Alternatives

### A — Application Startup Hook

**Rejected.**

Startup-triggered destructive maintenance makes application availability and storage mutation coupled. It also makes restart frequency influence maintenance behavior.

### B — In-Process Background Scheduler

**Candidate.**

Pros:
- simple deployment;
- no external infrastructure;
- direct composition with the existing runtime.

Cons:
- lifecycle and shutdown become scheduler concerns;
- duplicate execution becomes possible across multiple application instances;
- process restarts can interrupt schedules;
- operational guarantees become dependent on API process uptime.

### C — Explicit Maintenance Command / External Scheduler

**Preferred candidate for the MVP.**

Pros:
- destructive maintenance is explicit and operationally isolated;
- works with Windows Task Scheduler, cron, CI/CD, or another external scheduler;
- no always-running background worker;
- no new distributed-coordination problem.

Cons:
- deployment/operations must configure the trigger separately;
- scheduling is not self-contained inside the application.

### D — Persistent Internal Scheduler

**Deferred.**

This would introduce durable scheduling state, recovery semantics, locking, and a larger lifecycle boundary than M59 requires.

## Proposed Decision

M59 should expose a dedicated, non-HTTP maintenance invocation boundary that an external scheduler can call.

The application owns retention semantics; the operating environment owns when maintenance is invoked.

The trigger must:

1. load validated configuration;
2. invoke automatic retention once;
3. preserve M58 hard batch bounds;
4. return a deterministic success/failure result;
5. never bypass the M57 purge boundary;
6. remain safe when retention is disabled;
7. be idempotent when invoked repeatedly;
8. avoid application-startup invocation.

## Open Decisions

1. Should the maintenance entry point be a Python module command, a dedicated application service, or both?
2. What should the disabled result communicate: successful no-op or explicit disabled status?
3. Should overlapping invocations be prevented by an application lock, SQLite lock, or delegated to the external scheduler?
4. What retry responsibility belongs to the trigger versus M58/M57?
5. What minimum operational result should be emitted for scheduled execution?
6. Should the trigger be callable only by an operator/system identity, or remain outside the user-authenticated HTTP boundary entirely?
7. What exact cadence should documentation recommend, without making cadence part of domain policy?

## TDD Acceptance Shape

Before implementation is authorized, tests should cover:

- disabled retention produces no deletion;
- enabled retention invokes the existing M58 capability;
- repeated invocation is safe;
- no HTTP endpoint is required for maintenance execution;
- startup does not invoke retention;
- configuration failures fail safe;
- M57 remains the only physical deletion boundary;
- trigger failures do not mutate retention policy;
- deterministic maintenance result;
- overlap behavior is explicit and tested.

## Design Gate Rule

No implementation is authorized until the open decisions are explicitly accepted and the trigger boundary is recorded in the decision log and roadmap.
