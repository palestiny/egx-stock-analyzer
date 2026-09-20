# DEC-120 — M57 Physical Purge Design Gate

**Status:** Proposed  
**Date:** 2026-09-21  
**Milestone:** M57 — Analysis Run & Snapshot Physical Purge

## 1. Problem

M56 established accepted logical deletion for durable `AnalysisRun` records and `AnalysisResultRecord` snapshots.

M56 deliberately keeps physical purge outside the user-facing lifecycle capability. Logical deletion therefore removes resources from normal visibility but does not reclaim their durable storage.

M57 must determine whether, when, and how logically deleted analysis data can be physically removed without weakening M54/M55 ownership, M56 lifecycle invariants, auditability, or cross-store correctness.

This is a storage-lifecycle capability, not an analytical capability.

## 2. Desired Outcome

Define a bounded privileged maintenance capability that can physically purge eligible logically deleted analysis data while:

1. preserving M54/M55 ownership and authorization boundaries;
2. preserving M56 run/snapshot lifecycle coupling;
3. never purging visible or active analysis data;
4. handling correlated AnalysisRun, AnalysisRunOutcome, and AnalysisResultRecord records consistently;
5. remaining safe across restart and repeated execution;
6. providing deterministic eligibility and bounded execution;
7. maintaining required auditability;
8. making transaction and partial-failure semantics explicit.

## 3. In Scope

- physical purge eligibility;
- purge authority and operator-only boundary;
- relationship between logically deleted runs and correlated snapshots;
- independently deleted runless snapshots;
- AnalysisRunOutcome cleanup;
- references that can block purge;
- transaction boundaries;
- idempotency;
- concurrent analysis protection;
- bounded batch execution;
- restart behavior;
- audit events;
- deterministic tests;
- storage reclamation verification.

## 4. Explicitly Out of Scope

- automatic retention policy;
- user-facing deletion semantics already accepted by M56;
- undelete/recovery;
- changes to M54/M55 ownership;
- analytical calculations;
- ranking, alerts, notifications, or trading;
- scheduled-workflow lifecycle;
- database replacement;
- distributed garbage collection;
- object-storage archival;
- background-worker infrastructure unless explicitly required by the accepted design;
- changing normal read semantics for logically deleted records.

## 5. Current Architectural Boundary

```
Privileged Maintenance Trigger
            ↓
Physical Purge Application Capability
            ↓
Lifecycle / Authorization Boundary
            ↓
AnalysisRunStore + AnalysisResultStore
            ↓
Shared SQLite Transaction Boundary
```

The purge capability must not be implemented by React, HTTP handlers, or individual stores acting independently.

## 6. Current Constraints From M56

1. Logical deletion is already authoritative for normal visibility.
2. Physical purge is a separate privileged capability.
3. Automatic retention is disabled.
4. Deletion of active analysis is prohibited.
5. Run deletion hides correlated snapshots together.
6. Runless snapshots remain independently governed by M55 ownership.
7. Lifecycle mutations must not claim cross-store atomicity without a proven shared SQLite transaction boundary.
8. Management-audit recording is mandatory for destructive lifecycle requests.
9. M56 logical deletion is idempotent.
10. Existing ownership and non-enumerating authorization semantics remain unchanged.

## 7. Design Alternatives

### A — Immediate Physical Purge of Every Logically Deleted Record

**Advantages**
- simple mental model;
- fastest storage reclamation.

**Trade-offs**
- no recovery window;
- larger operational blast radius;
- harder to safely retry if a batch is interrupted.

### B — Explicit Privileged Purge of Eligible Records

**Advantages**
- separates user-facing deletion from irreversible maintenance;
- deterministic and auditable;
- can be bounded by explicit limits.

**Trade-offs**
- requires an operator maintenance workflow;
- storage may remain occupied until purge is invoked.

### C — Automatic Retention-Driven Purge

**Advantages**
- continuous storage control.

**Trade-offs**
- introduces policy and scheduling decisions;
- creates automatic destructive behavior;
- explicitly conflicts with M56's decision to defer automatic retention.

### D — Archive Then Purge

**Advantages**
- preserves historical data outside the primary database;
- allows stronger storage reclamation.

**Trade-offs**
- introduces archival storage, integrity verification, restore semantics, and additional infrastructure.

**Design candidate:** B. This preserves the explicit M56 separation between logical deletion and irreversible purge while avoiding automatic retention policy.

## 8. Accepted Decisions

### 8.1 Authority

Physical purge is operator-only and requires the existing privileged maintenance/management authorization boundary. No new role is introduced in M57.

This keeps M57 inside the established authorization model and avoids inventing a second identity hierarchy for a storage-maintenance operation.

### 8.2 Selection Model

The capability supports two explicit modes: explicit resource IDs, or preview/purge of the next eligible resources using deterministic eligibility and an explicit batch limit. An unrestricted request is never interpreted as delete-everything.

### 8.3 Eligibility

A resource is eligible only when it is logically deleted, not visible through normal lifecycle reads, and not active or otherwise protected by a known lifecycle constraint.

For an AnalysisRun, the run and all lifecycle-owned snapshots/outcomes must be in a purgeable deleted state. A visible or active run is never eligible.

A runless snapshot is independently eligible when its own logical-deletion state and ownership rules make it purgeable.

Unknown or unsupported future references are blockers, not silently ignored.

### 8.4 Correlated Data

An eligible AnalysisRun is purged together with its lifecycle-owned AnalysisRunOutcome rows and correlated AnalysisResultRecord snapshots in one transaction. Runless snapshots are purged independently.

M57 does not introduce a new relationship model; it uses the relationships already established by M54/M55/M56.

### 8.5 Transaction Boundary

Each lifecycle unit is deleted inside one shared SQLite transaction. The application capability owns the transaction boundary; individual stores must not commit independently during a purge.

If any required deletion fails, the transaction rolls back and no member of that lifecycle unit is considered purged.

### 8.6 Concurrency

Purge coordinates with active analysis by acquiring the SQLite write transaction before destructive deletion and re-checking eligibility inside that transaction. A resource that becomes active or otherwise ineligible before commit is not deleted.

No application-level distributed lock is introduced for the SQLite MVP.

### 8.7 Batching and Ordering

The MVP uses an explicit positive batch limit with a default of 100 lifecycle units per invocation. Eligibility is ordered by stable persisted identifier, ascending.

A batch contains complete lifecycle units; correlated rows do not consume separate lifecycle-unit slots. The limit is a safety bound, not a retention policy.

### 8.8 Failure Semantics

A single lifecycle-unit failure rolls back that unit and stops the current purge invocation.

The result reports successfully purged units before the failure plus the failing resource identity/error category.

This fail-stop behavior minimizes destructive blast radius and keeps restart behavior deterministic.

### 8.9 Restart and Idempotency

Purge is synchronous in M57. A process interruption rolls back the in-flight SQLite transaction. Successfully committed earlier lifecycle units remain purged.

Retrying the same request is safe: already-purged resources are absent and contribute no additional deletion.

### 8.10 Auditability

Every purge request produces a management-audit event containing the maintenance actor, operation identity, selection mode, requested limit/IDs, result status, and counts.

Each successfully purged lifecycle unit is represented in audit data by stable resource identity and operation identity before the destructive transaction commits.

Audit records do not depend on reading the deleted resource after commit.

### 8.11 Result Contract

The capability returns an immutable operation summary containing operation identity, selection mode, requested limit/IDs, purged lifecycle-unit count, removed snapshot/outcome counts, ordered purged resource IDs, and optional failure information.

Dry-run/preview returns eligible ordered resource IDs and counts without mutation or destructive audit events.

### 8.12 Legacy and Global Records

M57 does not purge unsupported legacy/global records unless they satisfy the same explicit lifecycle eligibility contract.

Any record whose ownership, relationship, or deletion state cannot be proven safe is skipped and reported as blocked rather than force-deleted.

### 8.13 Retention

Automatic retention remains disabled. No age threshold is introduced by M57. Physical purge happens only through the explicit privileged capability.

## 9. Design Trade-offs

- Explicit privileged purge over automatic retention: preserves the M56 separation between reversible logical lifecycle state and irreversible storage maintenance.
- One lifecycle unit per transaction: stronger cross-store consistency, at the cost of lower throughput.
- Fail-stop on uncertain destructive failure: smaller blast radius and deterministic recovery, at the cost of another invocation for later eligible units.
- Batch limit 100: bounded operational impact without pretending to be a retention policy.
- Stable-ID ordering: deterministic and easy to resume; avoids time-based ambiguity.
- Synchronous execution: avoids introducing workers and durable job infrastructure in the MVP.
- Existing operator authorization: avoids a new role while preserving privileged access.
- Preview/dry-run: improves operator safety without changing deletion policy.

## 10. Proposed Invariants

1. Only an explicitly authorized maintenance identity may physically purge records.
2. A visible record is never eligible for physical purge.
3. An active analysis run is never eligible for purge.
4. A correlated AnalysisRun and its lifecycle-owned snapshots/outcomes are purged as one coherent lifecycle unit.
5. AnalysisRunOutcome rows are not left orphaned.
6. Runless snapshots are independently eligible according to their logical-deletion and ownership state.
7. Physical purge does not reassign ownership.
8. Physical purge does not change normal read-side authorization semantics.
9. Purge is idempotent.
10. Cross-store deletion uses one proven SQLite transaction per lifecycle unit.
11. A failed lifecycle transaction leaves its durable state unchanged.
12. Purge execution is bounded and deterministic.
13. Automatic retention remains disabled.
14. Audit records do not depend on the deleted resource remaining readable after purge.
15. No analytical calculation occurs inside the purge capability.
16. Unsupported or unproven references block purge rather than being silently ignored.
17. A dry-run performs no destructive mutation.

## 11. TDD Acceptance Criteria

Implementation must cover at least:

- operator authorization and rejection of non-privileged identities;
- explicit-ID purge and deterministic eligibility selection;
- eligible deleted run purge;
- correlated snapshot and outcome purge;
- eligible runless snapshot purge;
- refusal to purge visible records;
- refusal to purge active analysis;
- refusal when lifecycle state is inconsistent;
- duplicate/repeated purge idempotency;
- batch limit of 100 and deterministic stable-ID ordering;
- fail-stop behavior after a lifecycle-unit failure;
- transaction rollback;
- restart/interruption behavior;
- mandatory management-audit recording;
- dry-run with no mutation;
- physical storage-row absence after successful purge;
- blocking unsupported/future references;
- preservation of M54/M55 ownership invariants;
- unchanged normal read behavior for non-deleted resources.

## 12. Decision Gate

**Status: Accepted — implementation is authorized for the M57 MVP defined here.**

Implementation boundary:

```
Privileged Maintenance Trigger
            ↓
PurgeAnalysisLifecycle
            ↓
Authorization + Lifecycle Eligibility
            ↓
Shared SQLite Transaction
      ↙                 ↘
AnalysisRun/Outcome   AnalysisResultRecord
            ↓
Management Audit
```

M57 must not introduce automatic retention, a new authorization role, background workers, archival storage, or changes to normal user-facing deletion semantics.

## 13. Revisit Conditions

Revisit this gate if the persistence technology changes, archival storage is introduced, cross-run references become concrete, legal/compliance retention requirements appear, or automatic retention becomes a product requirement.
