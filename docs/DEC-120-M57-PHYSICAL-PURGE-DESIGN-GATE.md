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

## 8. Open Questions

1. Is physical purge strictly operator-only?
2. Should the purge capability accept explicit resource IDs, a deletion-state query, or both?
3. What makes a logically deleted AnalysisRun eligible for purge?
4. Must all correlated snapshots be logically deleted before the run can be purged?
5. Should run outcomes always be purged with their parent run?
6. What makes a runless snapshot eligible?
7. Should any future durable reference block purge?
8. What happens when a logically deleted record is referenced by an unsupported legacy relationship?
9. Should purge operate synchronously?
10. What maximum batch size is appropriate?
11. Should one failed record fail the entire batch or allow other eligible records to continue?
12. How should a purge resume after process interruption?
13. How should concurrent analysis versus purge be coordinated?
14. What audit event is required for each purge request and each purged resource?
15. Should purge return counts, resource IDs, or only an operation summary?
16. What verification proves that storage rows were actually removed?
17. Is a separate maintenance authorization role required, or is existing operator authorization sufficient?
18. Should purge support dry-run/preview before irreversible deletion?
19. How should transaction rollback behave when a correlated multi-table deletion fails?
20. Should purge ever operate on system/global legacy records without an explicit operator confirmation boundary?

## 9. Proposed Invariants

1. Only an explicitly authorized maintenance identity may physically purge records.
2. A visible record is never eligible for physical purge.
3. An active analysis run is never eligible for purge.
4. A correlated AnalysisRun and its lifecycle-owned snapshots are purged as one coherent lifecycle unit.
5. AnalysisRunOutcome rows are not left orphaned.
6. Runless snapshots are independently eligible according to their logical-deletion state and ownership policy.
7. Physical purge does not reassign ownership.
8. Physical purge does not change normal read-side authorization semantics.
9. Purge is idempotent: retrying an already-purged resource does not recreate or corrupt state.
10. Cross-store deletion uses one proven SQLite transaction boundary.
11. A failed transaction leaves the durable lifecycle state unchanged.
12. Purge execution is bounded and deterministic.
13. Automatic retention remains disabled unless a separate design gate explicitly enables it.
14. Audit records do not depend on the deleted resource remaining readable after the purge.
15. No analytical calculation occurs inside the purge capability.

## 10. TDD Acceptance Shape

Before implementation, tests should cover at least:

- operator authorization;
- rejection of non-privileged purge;
- purge of an eligible deleted run;
- purge of correlated snapshots;
- purge of correlated outcomes;
- purge of an eligible runless snapshot;
- refusal to purge visible records;
- refusal to purge active analysis;
- refusal when required lifecycle state is inconsistent;
- repeated purge of an already-purged resource;
- bounded batch size;
- deterministic batch ordering;
- one-record failure behavior;
- transaction rollback;
- restart after interrupted purge;
- audit recording;
- storage-row absence after successful purge;
- protection of unsupported/future references;
- preservation of M54/M55 ownership invariants;
- no change to normal read behavior for non-deleted resources.

## 11. Recommended Direction — Not Yet Accepted

The current architecture supports evaluating:

- a dedicated privileged `PurgeAnalysisLifecycle` application capability;
- explicit operator-only authorization;
- eligibility based only on persisted logical-deletion state;
- explicit batch limits;
- deterministic ordering by stable persisted identifiers;
- one shared SQLite transaction per lifecycle unit;
- correlated run, outcome, and snapshot deletion in the same transaction;
- independent handling of runless snapshots;
- mandatory management-audit recording;
- optional dry-run as a read-only planning mode;
- no automatic retention.

These are recommendations only. They are not accepted product policy.

## 12. Decision Gate

**Status: Proposed — implementation is not authorized.**

M57 implementation must wait until the purge authority, eligibility, transaction, batching, failure, audit, and reference semantics are explicitly accepted.

## 13. Revisit Conditions

Revisit this gate if the persistence technology changes, archival storage is introduced, cross-run references become concrete, legal/compliance retention requirements appear, or automatic retention becomes a product requirement.
