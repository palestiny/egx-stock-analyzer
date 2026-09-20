# DEC-117 — M55 Analysis Snapshot Ownership Design Gate

**Status:** Proposed  
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

## Open Questions

1. Ownership authority: should a run-correlated snapshot inherit ownership from AnalysisRun, or should every snapshot persist its own owner UUID?
2. Manual analysis: should a user-created single-stock analysis produce an owned snapshot directly, create an AnalysisRun, or remain system/global?
3. Legacy snapshots: should pre-M55 snapshots remain system/global and operator-only, with no inferred owner?
4. Runless snapshots: how should newly created snapshots without an AnalysisRun be classified?
5. Consistency: if both snapshot and run owners exist, which invariant prevents divergence?
6. Read authorization: should AnalysisResultStore expose owner-aware queries while application capabilities retain policy decisions, matching M54?
7. API behavior: should unauthorized snapshot IDs and history requests return 404 to avoid enumeration?
8. Stock-history semantics: should a history query return only visible snapshots, or reject the query if any matching record is inaccessible?
9. Latest-result semantics: how should get(symbol) behave when the latest snapshot is not visible to the caller?
10. Operator visibility: should the existing operator identity see all user-owned and system/global snapshots?
11. Run-scoped access: should authorized run detail remain the authoritative path for snapshots correlated to a run?
12. Migration: can existing SQLite records be classified deterministically without reconstructing historical ownership?

## Proposed Invariants

1. A user must never read another user's snapshot through any snapshot or history capability.
2. Snapshot ownership must be deterministic and durable.
3. No owner is inferred from timestamps, IP/session state, or historical access.
4. A run-correlated snapshot must never be visible outside the authorization boundary of its owning run.
5. If a snapshot stores an owner UUID, a run-correlated snapshot owner must equal the run owner.
6. Legacy records must have an explicit system/global interpretation.
7. Authorization policy remains in application capabilities, not React.
8. Snapshot ownership must not affect analytical values or execution state.
9. Latest-result compatibility must remain explicit; authorization must not silently return another user's data.
10. No sharing or multi-owner semantics are introduced by M55.

## TDD Acceptance Shape

- user-owned snapshot persistence and reload;
- user cannot read another user's snapshot by ID;
- user cannot read another user's stock history;
- operator visibility of user-owned and system/global snapshots;
- run-correlated snapshot cannot escape run ownership;
- legacy snapshot behavior;
- manual single-stock analysis ownership;
- deterministic unauthorized 404 behavior where selected;
- latest-result behavior under ownership filtering;
- restart preserves ownership;
- existing authorized run detail and M53 outcome semantics remain unchanged.

## Design Gate Status

**Implementation is not authorized yet.**

The next step is to resolve the open ownership-model questions and record the accepted decision before modifying snapshot persistence, application read capabilities, or API/dashboard contracts.

## Revisit Conditions

- snapshot sharing becomes a requirement;
- organizations or team ownership are introduced;
- snapshots become publicly addressable resources;
- manual analysis is redesigned around a different durable run model;
- retention/deletion requirements require a different ownership lifecycle.