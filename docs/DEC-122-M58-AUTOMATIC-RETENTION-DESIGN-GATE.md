# DEC-122 — M58 Automatic Analysis Retention Design Gate

**Status:** Accepted  
**Date:** 2026-09-21  
**Milestone:** M58 — Automatic Analysis Retention

## 1. Problem

M56 established logical deletion and M57 established explicit privileged physical purge.

The current lifecycle therefore requires an operator to decide when eligible deleted data should be physically reclaimed. M58 must decide whether automatic retention is justified and, if so, what policy and execution boundary should govern it.

This is a lifecycle-policy capability, not an analytical capability.

## 2. Desired Outcome

Define an explicit, testable retention policy that can:

1. preserve the accepted M54/M55 ownership model;
2. preserve M56 logical-deletion semantics;
3. reuse M57 purge eligibility and transaction safety;
4. avoid deleting active or visible analysis data;
5. make retention policy explicit;
6. remain deterministic and auditable;
7. define how policy changes affect existing data;
8. define policy ownership and execution control;
9. remain safe across restart and repeated execution.

## 3. In Scope

- retention policy model;
- eligibility based on persisted lifecycle state and age;
- interaction between logical deletion and physical purge;
- whether retention applies to runs, runless snapshots, or both;
- policy ownership and configuration;
- manual/operator override boundaries;
- scheduling/trigger ownership;
- auditability;
- dry-run/preview semantics;
- idempotency and restart behavior;
- policy-version/configuration traceability;
- deterministic tests;
- operational safeguards.

## 4. Explicitly Out of Scope

- changing M54/M55 ownership semantics;
- changing M56 user-facing deletion semantics;
- changing M57 purge transaction semantics;
- undelete/recovery;
- archival storage;
- database replacement;
- distributed garbage collection;
- analytical calculations;
- ranking, signals, notifications, or trading;
- new authorization roles unless a separate gate proves the existing model insufficient.

## 5. Current Boundary

```
Retention Policy
      ↓
Retention Selection / Maintenance Application Capability
      ↓
Existing M57 PurgeAnalysisLifecycle
      ↓
Existing Lifecycle Eligibility + Shared SQLite Transactions
      ↓
SQLite
```

M58 should not reimplement destructive deletion. Its responsibility, if accepted, is to determine which already-purgeable lifecycle units have crossed the accepted retention boundary and invoke the existing purge capability.

## 6. Design Alternatives

### A — Keep Retention Fully Manual

No automatic retention policy is introduced. Operators continue invoking M57 purge explicitly.

**Advantages**
- smallest operational risk;
- no automatic destructive behavior;
- no arbitrary preservation window.

**Trade-offs**
- storage can grow indefinitely;
- reclamation depends on operational discipline.

### B — Age-Based Automatic Retention

A lifecycle unit becomes eligible after a configured age from a clearly defined lifecycle timestamp, then uses the existing M57 purge capability.

**Advantages**
- simple and explainable;
- deterministic;
- directly limits storage age.

**Trade-offs**
- requires choosing a preservation window;
- different data classes may have different useful lifetimes.

### C — Count-Based Retention

Keep only the most recent N eligible lifecycle units/snapshots per defined scope.

**Advantages**
- predictable storage volume;
- independent of calendar time.

**Trade-offs**
- behavior changes with analysis frequency;
- harder to explain as a business preservation policy.

### D — Hybrid Age + Count Policy

Combine age and count limits with an explicit precedence rule.

**Advantages**
- combines time and storage bounds.

**Trade-offs**
- more configuration and harder reasoning;
- greater policy complexity.

### Engineering Recommendation

For an MVP, B — age-based retention is the simplest policy to explain and test if the product owner determines that automatic deletion is actually required.

This is a recommendation only. No retention window, scope, or automatic execution policy is accepted by this document.

## 7. Accepted Policy Decisions

The owner accepted the following M58 policy direction:

1. Automatic retention is required.
2. The retention clock starts at logical deletion time (`deleted_at`).
3. Scope covers both deleted AnalysisRuns with their correlated lifecycle data and runless deleted snapshots, subject to existing M57 eligibility.
4. The preservation period is configurable as a system policy. The actual retention duration remains an explicit open product-policy value and is not yet selected.
5. Policy ownership is system/operator-level, not per-user.
6. A changed policy applies to the current persisted state when retention executes; records do not receive speculative per-record policy versions in this MVP.
7. Automatic execution is controlled maintenance/scheduler-driven rather than application-startup-driven. The concrete trigger must be mapped to an existing project mechanism during implementation design; no destructive startup hook is authorized.
8. Every automatic-retention invocation has a hard batch bound.
9. Dry-run/preview is available and non-destructive.
10. Automatic retention uses a distinct auditable operation identity from manual M57 purge.
11. Automatic retention is disabled by default and requires explicit enablement.
12. Invalid or unavailable configuration fails safe: no automatic deletion occurs.

The only remaining policy decision required before implementation is the actual preservation duration.

## 8. Proposed Invariants

1. Automatic retention never purges visible resources.
2. Automatic retention never purges active resources.
3. Only records already eligible under M57 may be physically purged.
4. M58 does not duplicate M57 transaction or deletion semantics.
5. Retention policy evaluation is deterministic for the same persisted state and policy.
6. Policy configuration is explicit and validated.
7. Invalid retention configuration fails safely and never widens deletion scope.
8. Automatic retention is bounded per invocation.
9. Repeated execution is idempotent.
10. Every destructive automatic-retention invocation is auditable.
11. Dry-run performs no destructive mutation.
12. Ownership is never reassigned by retention.
13. Legacy records are not assigned speculative retention semantics.
14. No analytical calculation occurs inside retention.
15. Retention policy does not change normal read authorization or logical-deletion semantics.
16. Existing M57 purge remains independently usable.

## 9. Engineering Findings Before Policy Decision

The current lifecycle persistence records `deleted_at` on both `analysis_runs` and `analysis_results`. M56 sets this timestamp when logical deletion occurs, and M57 only purges records that are already logically deleted.

Therefore an age-based policy can be implemented without inventing a new retention timestamp if the owner chooses logical deletion time as the retention clock. This is an implementation-readiness finding, not an accepted policy decision.

Using `analysis_runs.created_at` as the retention clock has different semantics: a record could become eligible based on age even if it was logically deleted recently. The timestamp choice must therefore remain explicit.

The existing M57 capability already provides the destructive boundary, eligibility protection, batching, transaction handling, idempotency, and audit mechanism that M58 can reuse. M58 should add policy evaluation and triggering rather than another deletion path.

## 10. TDD Acceptance Shape

Before implementation is authorized, tests should cover at least:

- policy validation;
- boundary timestamps;
- eligible versus non-eligible deleted records;
- visible/active protection;
- run-correlated lifecycle units;
- runless snapshots if included;
- deterministic ordering;
- batch bounds;
- policy-disabled behavior;
- invalid configuration fail-safe behavior;
- repeated execution/idempotency;
- audit distinction between manual and automatic maintenance;
- reuse of M57 purge semantics;
- restart-safe execution;
- policy-change behavior;
- ownership preservation;
- unchanged normal read semantics.

## 11. Design Gate Decision

**Status: Accepted with one remaining policy value — implementation is not yet authorized.**

The owner has accepted the M58 policy direction above. The preservation duration remains intentionally open because it is a product/lifecycle value rather than an implementation detail.

M57 explicit privileged purge remains the authoritative physical-reclamation mechanism until the retention duration is selected and the implementation design gate is closed.

## 12. Revisit Conditions

Revisit this gate if storage growth, compliance requirements, user expectations, archival requirements, or operational evidence changes the need for automatic retention.
