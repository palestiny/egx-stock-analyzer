# DEC-117 — M55 Analysis Snapshot Ownership Design Gate

**Status:** Accepted  
**Date:** 2026-09-20  
**Milestone:** M55 — Analysis Snapshot Ownership

## Context

M54 establishes durable ownership for AnalysisRun and protects run-scoped read capabilities by authenticated ownership.

The durable analysis-result layer is broader than AnalysisRun. AnalysisResultStore contains historical AnalysisResultRecord snapshots that can be correlated to an AnalysisRun, produced by single-stock analysis without an AnalysisRun, addressed directly by snapshot identity, and queried through stock-history capabilities.

M54 explicitly leaves standalone snapshot/history ownership unchanged.

This creates the next security boundary:

> Can an authenticated user access an analysis snapshot merely because they know its stock or snapshot identifier, even when the snapshot belongs to another user's analysis activity?

## Desired Outcome

Define a durable and reusable ownership boundary for analytical snapshots so that:

1. user-created analytical data has explicit authorization semantics;
2. snapshots correlated to an owned AnalysisRun cannot escape that ownership boundary;
3. direct/manual stock analysis has deterministic ownership semantics;
4. legacy snapshots are handled explicitly without inferred ownership;
5. snapshot/history APIs use one application-level authorization rule;
6. ownership survives restart;
7. existing latest-result compatibility remains intact;
8. analytical calculations, scoring, ranking, retry behavior, and provider behavior remain unchanged.

## Scope

### In Scope

- ownership semantics for AnalysisResultRecord;
- relationship between snapshot ownership and AnalysisRun ownership;
- manual single-stock analysis ownership;
- legacy/global snapshot migration semantics;
- snapshot-by-ID authorization;
- stock-history authorization;
- run-scoped snapshot authorization;
- API/dashboard behavior for inaccessible snapshots;
- SQLite persistence and restart behavior;
- compatibility with existing latest-result and historical-read contracts.

### Explicitly Out of Scope

- sharing snapshots;
- organization/team ownership;
- ACLs or delegated access;
- public snapshot links;
- changing analysis algorithms;
- changing retry semantics;
- notification ownership;
- trading/portfolio permissions;
- real-time collaboration;
- retention/deletion policy unless required only to preserve ownership integrity.

## Current Boundary

```
AuthenticatedIdentity
        ↓
Analysis Snapshot Read Capability
        ↓
AnalysisResultStore
        ↓
AnalysisResultRecord
        ↙
AnalysisRun(owner)
```

A snapshot may have an analysis_run_id, but not every snapshot necessarily has one. M55 must explicitly define the authority for snapshots in both cases.

## Why M54 Is Not Sufficient

M54 protects the AnalysisRun resource, but that does not automatically protect direct snapshot or stock-history access.

If snapshot ownership is only assumed from run ownership, direct/manual snapshots and legacy snapshots remain ambiguous. If ownership is copied independently into every read path without one authoritative rule, the system risks authorization drift.

## Alternatives

### A — Derive Snapshot Ownership Only From AnalysisRun

A snapshot with an analysis_run_id inherits its run owner. Snapshots without a run remain system/global.

Advantages: one ownership source for market-wide snapshots; no duplicate owner field; preserves run correlation.

Trade-offs: manual user-created snapshots have no natural owner unless manual analysis is also converted into a run; direct snapshot authorization needs a special rule for runless records.

### B — Persist an Optional Owner UUID on Every Snapshot

AnalysisResultRecord stores its own immutable owner_user_id. For run-correlated snapshots, creation must ensure the snapshot owner matches the AnalysisRun owner.

Advantages: direct snapshot authorization is explicit; manual single-stock analysis can be user-owned without a synthetic run; stock-history queries can be owner-scoped directly.

Trade-offs: duplicates ownership metadata; requires a consistency invariant between snapshot and run ownership; requires migration and query changes.

### C — Separate Snapshot ACL / Ownership Mapping

Keep snapshot records unchanged and add a separate ownership mapping.

Advantages: supports future sharing and multiple principals.

Trade-offs: creates a second authorization source of truth and expands scope unnecessarily.

Assessment: Deferred.

## Accepted Decisions

### 1. Ownership Authority

M55 persists an optional immutable `owner_user_id` directly on every new `AnalysisResultRecord`.

For a snapshot correlated to an `AnalysisRun`, the snapshot owner must equal the run owner. A system/global run therefore produces snapshots with no owner.

This deliberately duplicates the owner identity at the snapshot boundary. The duplication is accepted because snapshot reads are a first-class capability and must remain authorizable without reconstructing ownership through another store.

### 2. Manual Single-Stock Analysis

A user-authenticated manual analysis creates a runless snapshot owned directly by that authenticated user. It does not create a synthetic `AnalysisRun`.

System/operator-triggered manual analysis remains system/global when no user owner is supplied.

This preserves the existing single-stock execution semantics while giving user-created analytical data an explicit owner.

### 3. Legacy Snapshots

Existing snapshots created before M55 have no inferred owner and remain system/global.

Ownership is never reconstructed from timestamps, historical access, scheduled-workflow ownership, or other indirect evidence.

Regular users therefore cannot access legacy/global snapshots through owner-scoped snapshot/history capabilities; the existing operator identity can access them.

### 4. Runless Snapshots

A new runless snapshot has exactly one of these states:

- `owner_user_id = authenticated user UUID` for a user-created analysis;
- `owner_user_id = NULL` for a system/global analysis.

No third ownership mode is introduced.

### 5. Consistency Invariant

When both snapshot and run are present, the persistence/application boundary must enforce:

```
snapshot.analysis_run_id != NULL
    ⇒ snapshot.owner_user_id == analysis_run.owner_user_id
```

A mismatch is an explicit application/persistence error. The system must never silently repair ownership by choosing one side.

### 6. Read Authorization

`AnalysisResultStore` exposes owner-aware retrieval primitives, while application capabilities remain responsible for authorization policy.

The store may return records according to an explicit visibility scope:

- operator/system scope: all snapshots;
- user scope: snapshots whose `owner_user_id` equals the authenticated user's UUID.

Authorization logic is not moved into React or raw SQLite callers.

### 7. Snapshot and History Access

Unauthorized snapshot-by-ID access behaves as not found.

Stock-history queries return only snapshots visible to the caller. They do not fail merely because unrelated inaccessible snapshots exist for the same symbol.

This prevents one user's history from becoming an enumeration channel while allowing the query to remain a useful read capability.

### 8. Latest-Result Semantics

`get(symbol)` and latest-report reads use the caller's visibility scope.

For a regular user, the latest visible snapshot is the latest snapshot owned by that user. A newer snapshot belonging to another user must not cause the user's query to return another user's data or an authorization error revealing that data exists.

For the operator/system scope, existing latest-result semantics remain unchanged across all snapshots.

### 9. Run-Scoped Access

An authorized `GetAnalysisRun` remains the authoritative entry point for run-scoped access.

Its correlated snapshots must also satisfy the snapshot/run ownership invariant. Run authorization cannot be used to expose a snapshot whose persisted owner disagrees with the run owner.

### 10. Operator Visibility

The existing operator identity may read both user-owned and system/global snapshots.

No new role or permission model is introduced by M55.

### 11. Migration and Persistence

SQLite adds a nullable `owner_user_id` column to the snapshot table.

Existing rows migrate with `NULL` ownership. No historical owner is inferred.

New writes persist the owner atomically with the snapshot. Restart must preserve the exact owner UUID.

### 12. API and Dashboard Boundary

API capabilities pass the authenticated identity into application read/use-case boundaries. React remains presentation-only.

Unauthorized snapshot/run/history requests use the established non-enumerating 404 behavior where a resource-specific response exists.

M55 does not introduce sharing, ACLs, or public snapshot access.

## Design Gate Status

**Status: Accepted — implementation is authorized for the M55 Analysis Snapshot Ownership MVP.**

The implementation must establish ownership consistently across persistence, manual analysis, run-correlated snapshots, snapshot-by-ID reads, stock history, latest-result reads, and the existing authorized run-detail path.

## TDD Acceptance Criteria

- user-owned runless snapshot persists and reloads with its owner UUID;
- a user cannot read another user's snapshot by ID;
- a user cannot read another user's stock history;
- operator can read user-owned and system/global snapshots;
- run-correlated snapshot owner always matches run owner;
- legacy snapshots remain global/unowned after migration;
- manual single-stock analysis records the authenticated user as owner;
- unauthorized resource-specific reads return non-enumerating 404 behavior;
- latest-result reads return the latest visible snapshot rather than another user's newer snapshot;
- restart preserves ownership;
- authorized run detail remains readable and M53 outcome semantics remain unchanged;
- owner mismatch is rejected rather than silently repaired.

## Revisit Conditions

- snapshot sharing becomes a requirement;
- organizations or team ownership are introduced;
- snapshots become publicly addressable resources;
- manual analysis is redesigned around a different durable run model;
- retention/deletion requirements require a different ownership lifecycle.