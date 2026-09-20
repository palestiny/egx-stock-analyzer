# DEC-118 — M56 Analysis Snapshot Retention & Deletion Design Gate

**Status:** Proposed  
**Date:** 2026-09-20  
**Milestone:** M56 — Analysis Snapshot Retention & Deletion

## 1. Problem

M20 introduced durable historical analysis snapshots and M55 established explicit snapshot ownership. The project currently has no deliberate lifecycle policy for how long analytical snapshots remain available or how an authorized owner can remove them.

Ownership and retention are intentionally separate concerns. M55 explicitly deferred retention/deletion so that ownership semantics would not accidentally become a deletion policy.

Without an explicit lifecycle boundary, the system has no documented answer for whether snapshots are retained indefinitely, whether users may delete their own snapshots, whether deletion is hard or soft, how deletion interacts with AnalysisRun correlation, what happens to latest-result/history reads, or how SQLite integrity and restart behavior are guaranteed.

## 2. Goal

Define a narrow, auditable lifecycle boundary for analytical snapshots that respects M55 ownership, keeps retention/deletion separate from analytical execution, preserves AnalysisRun correlation integrity, defines authorization before implementation, makes deletion deterministic and testable, and avoids a generic retention framework prematurely.

## 3. In Scope

- snapshot retention policy;
- explicit deletion capability;
- deletion authorization and granularity;
- behavior for snapshots correlated to an AnalysisRun;
- legacy/system/global snapshot behavior;
- latest-result and history behavior after deletion;
- SQLite transactional semantics and restart durability;
- auditability requirements;
- API/application boundary implications.

## 4. Out of Scope

- automated archival to external storage;
- cloud/object-storage lifecycle management;
- generic retention framework for every project entity;
- scheduled cleanup jobs;
- legal/compliance retention policy claims;
- notification/trading behavior;
- analytical recalculation;
- changing snapshot ownership semantics;
- deleting scheduled workflow executions;
- deleting AnalysisRun records unless a later design explicitly requires it.

## 5. Current Constraints

M55 establishes that new snapshots have an optional immutable owner; run-correlated snapshots must match their AnalysisRun ownership; regular users may access only their own snapshots; the operator can access user-owned and system/global snapshots; legacy pre-M55 snapshots remain unowned/system-global; and snapshot reads use non-enumerating authorization behavior.

M56 must not weaken these constraints.

## 6. Alternatives

### A — Indefinite retention, no deletion

Keep all snapshots permanently.

**Advantages:** simplest lifecycle, strongest historical continuity, no deletion race or referential-integrity behavior.

**Trade-offs:** unbounded SQLite growth, no user control over obsolete snapshots, and an eventual storage-management problem.

### B — Explicit hard deletion

Provide an authorized application capability to permanently delete selected snapshots.

**Advantages:** simple mental model, bounded storage when deletion is used, and a clear present/absent lifecycle.

**Trade-offs:** permanent historical loss, explicit run-correlation behavior is required, concurrent reads/deletes need transaction semantics, and physical deletion may conflict with future audit requirements.

### C — Soft deletion / tombstones

Mark snapshots deleted while retaining a minimal lifecycle record.

**Advantages:** stronger auditability, persistent identity, and possible future recovery.

**Trade-offs:** storage is retained, every read must exclude deleted records, authorization becomes more complex, and a lifecycle-state concept is introduced early.

### D — Retention policy plus background cleanup

Define a time-based retention period and remove expired snapshots automatically.

**Advantages:** predictable storage growth and less manual maintenance.

**Trade-offs:** requires scheduling/cleanup semantics, expiration becomes a product decision, automated deletion can surprise users, and lifecycle concurrency/recovery becomes necessary.

## 7. Candidate Direction

The narrowest candidate for M56 is **explicit authorized deletion without automatic expiration**.

Under this candidate, deletion is an application capability; authorization reuses M55 ownership; regular users delete only owned snapshots; operator behavior is explicitly defined; deletion is transactional; deleting a snapshot does not delete its AnalysisRun; a run may remain readable with fewer correlated snapshots; latest-result queries exclude deleted records; scheduled workflow lifecycle records are unaffected; and automatic cleanup remains deferred.

This is a candidate, not yet an accepted architectural decision.

## 8. Open Decisions

1. Retention model: indefinite, explicit deletion, automatic retention, or a combination.
2. Deletion granularity: single snapshot, all snapshots for a symbol, all snapshots in a run, or multiple granularities.
3. User authority: only owned snapshots or snapshots from runs they own.
4. Operator authority: user-owned snapshots as well as system/global, or system/global only.
5. Run-correlated deletion: whether deleting one snapshot may leave a run partially represented.
6. Hard vs soft deletion.
7. Latest-result semantics after deletion.
8. Stock-history and comparison semantics after deletion.
9. Concurrency: compare-and-delete guard versus transactional existence check.
10. Whether deletion creates a durable management-audit event.
11. Whether automatic cleanup belongs in M56 or a later milestone.
12. Whether pre-M55 unowned/system-global snapshots may be deleted.

## 9. Proposed TDD Acceptance Shape

- authorized owner can delete an owned snapshot;
- unauthorized user receives non-enumerating not-found behavior;
- operator behavior follows the accepted policy;
- deleting one snapshot does not delete unrelated snapshots;
- run-correlated deletion preserves accepted AnalysisRun semantics;
- latest-result excludes deleted snapshots;
- stock history excludes deleted snapshots;
- comparison handles deleted snapshots according to the accepted contract;
- deletion survives restart;
- concurrent deletion/read behavior is deterministic;
- persistence rollback leaves no partial deletion;
- legacy snapshot behavior follows the accepted policy.

## 10. Design Gate Rule

No implementation should begin until the open decisions above are recorded as accepted decisions.

M56 must not silently turn snapshot ownership into a retention policy, and it must not introduce automatic cleanup merely because durable snapshots exist.

## 11. Related Decisions

- docs/DEC-111-M49-ANALYSIS-RUN-GROUPING-DESIGN-GATE.md
- docs/DEC-117-M55-ANALYSIS-SNAPSHOT-OWNERSHIP-DESIGN-GATE.md