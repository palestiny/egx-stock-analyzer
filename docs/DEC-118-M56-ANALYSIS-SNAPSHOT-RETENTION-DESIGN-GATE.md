# DEC-118 — M56 Analysis Snapshot Retention & Deletion Design Gate

**Status:** Proposed  
**Date:** 2026-09-20  
**Milestone:** M56 — Analysis Snapshot Retention & Deletion

## Context

M55 established durable ownership for analytical snapshots and explicitly deferred retention/deletion.

The system now preserves immutable analysis snapshots across recurring runs and supports user-scoped access. Without an explicit lifecycle policy, snapshot storage grows indefinitely and deletion semantics remain undefined.

Retention is not only a storage concern. Deleting a snapshot can affect latest-result behavior, historical queries, comparison/performance capabilities, AnalysisRun detail, ownership semantics, and restart durability.

## Desired Outcome

Define a bounded, explicit lifecycle for analytical snapshots that:

1. preserves ownership and authorization integrity;
2. keeps AnalysisRun correlation consistent;
3. distinguishes retention policy from manual deletion;
4. makes deletion deterministic and testable;
5. prevents accidental loss of authoritative read models;
6. preserves latest-result compatibility;
7. defines operator versus user deletion authority;
8. remains independent of trading, notifications, and analytical calculation.

## Scope

### In Scope

- retention policy semantics for AnalysisResultRecord;
- explicit deletion capability;
- ownership-aware deletion authorization;
- interaction with AnalysisRun;
- behavior of latest-result and historical reads after deletion;
- comparison and performance behavior after deletion;
- transactional SQLite deletion;
- restart behavior;
- auditability requirements for destructive operations;
- tests for ownership, correlation, and lifecycle invariants.

### Explicitly Out of Scope

- deleting AnalysisRuns as part of this milestone;
- deleting scheduled workflow executions or lifecycle history;
- automatic database vacuum/compaction tuning;
- archival to object storage;
- cross-user sharing;
- trading/portfolio lifecycle;
- notification delivery history;
- changing analytical calculations;
- changing snapshot ownership rules established by M55.

## Current Boundary

AuthenticatedIdentity
        ↓
Snapshot Lifecycle Capability
        ↓
AnalysisResultStore
        ↓
AnalysisResultRecord
        ↙
AnalysisRun(owner)

M56 should extend the existing application/persistence boundary rather than introducing deletion logic into API handlers, React, or raw SQLite callers.

## Alternatives

### A — Time-Based Automatic Retention

Snapshots older than a configured retention window are eligible for automatic deletion.

Advantages: bounded storage growth and predictable cleanup.

Trade-offs: age alone may delete snapshots still useful for comparison or audit; the retention clock must be defined; automatic destructive behavior needs strong testing and observability.

### B — Count-Based Retention

Keep only the latest N snapshots per symbol and delete older ones.

Advantages: predictable storage bound per symbol and simple operational reasoning.

Trade-offs: symbols with different analysis frequencies receive different time coverage and important historical snapshots may disappear unexpectedly.

### C — Explicit User/Operator Deletion Only

Do not automatically delete snapshots. Provide a deliberate destructive capability.

Advantages: no hidden data loss and simpler initial lifecycle.

Trade-offs: storage remains unbounded and requires clear authorization and confirmation semantics.

### D — Hybrid Retention + Explicit Deletion

Use a documented automatic retention policy while also allowing authorized explicit deletion.

Advantages: bounds long-term storage while supporting intentional cleanup.

Trade-offs: highest policy complexity and requires clear precedence and audit semantics.

### Current Recommendation for Design Discussion

D — Hybrid Retention + Explicit Deletion is the primary candidate for evaluation because the system is now both multi-user and historical. This is a design proposal, not an accepted decision.

## Open Questions

1. What is the authoritative retention clock: analysis date, snapshot creation time, or another persisted timestamp?
2. Should retention be global, per user, or configurable by operator?
3. What minimum historical window must be preserved?
4. Should the latest visible snapshot for each symbol be protected from automatic deletion?
5. Should snapshots referenced by an AnalysisRun be protected?
6. Can a snapshot used by comparison/performance be deleted, and what should subsequent reads return?
7. Does deleting one snapshot ever delete or mutate its AnalysisRun?
8. Who may explicitly delete: operator, owner, or both?
9. Should deletion be soft-delete or physical deletion?
10. What audit record is required for destructive operations?
11. Should automatic retention be synchronous during writes or a separate scheduled maintenance capability?
12. What happens when retention encounters a partially correlated or legacy snapshot?
13. Should retention run inside the existing scheduler boundary or remain an explicit maintenance use case?
14. What transaction guarantees are required when deleting a snapshot and related metadata?
15. What storage-growth evidence is sufficient to justify automatic retention in the MVP?

## Invariants

1. Snapshot ownership semantics from M55 remain unchanged.
2. A snapshot/run ownership mismatch is never repaired by deletion.
3. Deleting a snapshot must not mutate analytical results that remain stored elsewhere.
4. Latest-result queries must remain deterministic after deletion.
5. Unauthorized users must not be able to delete another user's snapshot.
6. Operator/system authorization must remain consistent with existing ownership rules.
7. A deleted snapshot must not remain readable through another application read path.
8. Deletion must not silently create or alter an AnalysisRun.
9. Legacy/global snapshot semantics remain explicit.
10. Retention policy must be deterministic and testable without wall-clock sleeps.
11. Destructive persistence must be transactional.
12. React and HTTP handlers remain transport/presentation boundaries.

## TDD Acceptance Shape

- authorized owner deletion;
- unauthorized user deletion;
- operator deletion;
- missing snapshot behavior;
- legacy/global snapshot behavior;
- deletion of a run-correlated snapshot;
- latest-result behavior after deletion;
- history behavior after deletion;
- comparison/performance behavior after deletion;
- restart after deletion;
- retention eligibility calculation;
- protected latest snapshot semantics if selected;
- transaction rollback on deletion failure;
- audit behavior if required;
- deterministic behavior around equal timestamps and boundaries.

## Design Gate Decision

**Status: Proposed — implementation is not authorized.**

M56 implementation must not begin until the retention/deletion policy, ownership authority, run-correlation behavior, and destructive-operation audit requirements are explicitly accepted.

## Revisit Conditions

- storage architecture changes;
- snapshots become externally archived;
- legal/compliance retention requirements appear;
- organizations or shared ownership are introduced;
- AnalysisRun deletion becomes a separate lifecycle requirement;
- the product no longer requires historical snapshots.