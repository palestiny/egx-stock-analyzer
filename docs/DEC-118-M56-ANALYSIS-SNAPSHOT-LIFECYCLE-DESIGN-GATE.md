# DEC-118 — M56 Analysis Snapshot Lifecycle Design Gate

**Status:** Proposed  
**Date:** 2026-09-20  
**Milestone:** M56 — Analysis Snapshot Lifecycle

## Context

M55 established explicit ownership for durable analysis snapshots and made ownership part of the persistence/read boundary.

M55 intentionally deferred retention and deletion policy. The repository can now accumulate analysis snapshots across recurring market runs and manual analyses, while ownership rules distinguish user-owned and system/global data.

The next lifecycle question is:

> Who is allowed to delete or retain analytical snapshots, what happens to correlated run data, and how can lifecycle operations preserve ownership, auditability, and historical-read integrity?

This gate exists before implementation so lifecycle semantics are explicit rather than emerging accidentally from a storage operation.

## Desired Outcome

Define a bounded MVP for analytical snapshot lifecycle management that:

1. makes retention/deletion ownership explicit;
2. prevents one user from deleting another user's snapshots;
3. preserves referential integrity with AnalysisRun correlation;
4. distinguishes active snapshots from intentionally deleted data;
5. avoids changing analytical calculations or execution semantics;
6. provides deterministic application-level behavior;
7. keeps lifecycle policy independent from React and raw SQLite.

## In Scope

- snapshot deletion semantics;
- owner authorization for lifecycle operations;
- operator/system lifecycle authority;
- interaction with AnalysisRun correlation;
- latest-result behavior after deletion;
- historical-read behavior after deletion;
- transactional persistence semantics;
- testability and restart behavior;
- bounded retention-policy direction.

## Explicitly Out of Scope

- snapshot sharing;
- organization/team ownership;
- public deletion APIs;
- automated background garbage collection;
- legal/compliance retention requirements;
- archival to external storage;
- changing analysis algorithms;
- changing run execution semantics;
- notification deletion;
- scheduled-workflow execution deletion.

## Current Boundary

    AuthenticatedIdentity
            ↓
    Snapshot Lifecycle Application Capability
            ↓
    AnalysisResultStore
            ↓
    AnalysisResultRecord
            ↙
    AnalysisRun(owner)

Lifecycle operations must reuse the existing ownership boundary rather than create a second authorization model.

## Alternatives

### A — Hard Delete Snapshots

Remove the snapshot row from durable storage.

**Advantages**
- simple storage semantics;
- no long-term deleted-record storage;
- latest/history queries naturally exclude deleted rows.

**Trade-offs**
- destructive and difficult to audit;
- run correlation can lose evidence of a previously successful snapshot;
- accidental deletion cannot be reconstructed from the application store.

### B — Soft Delete Snapshots

Keep the record but mark it deleted and exclude it from normal reads.

**Advantages**
- preserves durable history of lifecycle state;
- allows audit/recovery-oriented behavior later;
- can preserve correlation metadata.

**Trade-offs**
- every read must consistently exclude deleted records;
- storage grows indefinitely unless paired with retention;
- creates a new lifecycle state that must be defined carefully.

### C — Immutable Snapshot Store + Separate Tombstones

Keep snapshot data immutable and record deletion intent in a separate lifecycle/tombstone store.

**Advantages**
- preserves immutable analytical records;
- explicit lifecycle history;
- supports future archival/deletion workflows.

**Trade-offs**
- introduces a second persistence source of truth;
- more complex queries and authorization;
- disproportionate to the current MVP.

**Initial assessment:** A and B are viable MVP candidates. C is deferred.

## Open Questions

1. Should M56 use hard delete or soft delete?
2. Can a user delete a snapshot that is correlated to an owned AnalysisRun?
3. Can an operator delete system/global or user-owned snapshots?
4. Does deleting the last visible snapshot affect AnalysisRun history?
5. Should an AnalysisRun retain its outcome correlation when a snapshot is deleted?
6. Should the latest-result capability fall back to the next visible snapshot after deletion?
7. Is deletion one snapshot at a time, or should bounded bulk deletion be included?
8. Is automated retention policy part of M56, or should M56 define only explicit deletion?
9. What audit evidence is required for deletion?
10. Should deleted snapshot IDs remain non-enumerable and return 404?

## Proposed Invariants

1. Lifecycle authorization follows the same snapshot ownership boundary established by M55.
2. A lifecycle operation cannot modify another user's snapshot.
3. Deleting a snapshot must not silently delete or mutate its AnalysisRun.
4. AnalysisRun ownership remains authoritative for run access.
5. Latest-result and history reads must never return a deleted snapshot.
6. Snapshot lifecycle changes must be atomic at the persistence boundary.
7. Analytical execution, scoring, ranking, retries, and provider behavior remain unchanged.
8. No bulk/background retention engine is introduced without a separate operational decision unless explicitly accepted by this gate.
9. Deleted resource-specific reads should remain non-enumerating.

## TDD Acceptance Shape

Before implementation, tests should establish at least:

- owner can delete an owned snapshot;
- user cannot delete another user's snapshot;
- operator lifecycle behavior is explicit;
- deleting a run-correlated snapshot does not delete the run;
- latest visible snapshot skips deleted data;
- historical queries exclude deleted snapshots;
- restart preserves lifecycle state;
- deletion is atomic;
- deleting an already-deleted/non-visible snapshot has deterministic behavior;
- ownership invariants remain enforced.

## Design Gate Status

**Status: Proposed — implementation is not authorized by this document yet.**

The next action is to resolve the open questions and record the accepted lifecycle decision before implementation.

## Revisit Conditions

Revisit this gate if:

- snapshot sharing or team ownership is introduced;
- legal/compliance retention requirements appear;
- external archival becomes necessary;
- analysis runs become independently deletable resources;
- lifecycle operations require distributed/background execution.
