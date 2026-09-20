# DEC-116 — M54 Analysis Run Ownership Design Gate

**Status:** Proposed  
**Date:** 2026-09-20  
**Milestone:** M54 — Analysis Run Ownership

## Context

M49 introduced durable AnalysisRun identity and M50/M51/M52/M53 established durable run history, discovery, outcome completeness, and authenticated read surfaces.

The current analysis-run boundary still uses the legacy system/operator visibility model: authenticated users can access analysis runs without a durable owner relationship.

The project now has multi-user identity and ownership for scheduled workflow executions. Analysis runs are the remaining major durable execution artifact without explicit user ownership.

This creates a concrete boundary question:

> Which authenticated user is allowed to discover, inspect, and initiate a market-wide AnalysisRun?

M54 is proposed as a security/ownership boundary only. It must not change analytical calculations, run outcome semantics, persistence of successful snapshots, or retry behavior.

## Desired Outcome

Provide durable ownership semantics for AnalysisRun so that:

1. user-created market-wide runs are associated with one authenticated user;
2. users can list and inspect only their own runs;
3. operator/system identity can retain controlled visibility of system/global runs;
4. scheduled system-created runs remain compatible with existing workflow ownership semantics;
5. ownership survives restart;
6. M50–M53 run/outcome read semantics remain intact within the authorized visibility boundary;
7. ownership is enforced in the application layer rather than reconstructed by React or inferred from timestamps.

## Scope

### In Scope

- AnalysisRun owner identity;
- creation-time ownership;
- legacy/global run migration semantics;
- ownership-aware AnalysisRunStore reads;
- ownership-aware GetAnalysisRun/ListAnalysisRuns;
- market-wide execution ownership input;
- API authorization integration;
- dashboard behavior for inaccessible runs;
- restart/authorization tests.

### Explicitly Out of Scope

- organization/team ownership;
- sharing one run with multiple users;
- role redesign;
- public run sharing;
- changing stock-analysis rules;
- changing retry policy;
- workflow ownership redesign;
- notification ownership;
- trading/portfolio permissions;
- real-time collaboration.

## Problem Boundary

```
Authenticated Identity
        ↓
RunMarketAnalysis / scheduled trigger
        ↓
AnalysisRun(owner)
        ↓
AnalysisRunStore
        ↓
GetAnalysisRun / ListAnalysisRuns
        ↓
API
        ↓
Dashboard
```

The owner is authorization metadata. It does not become part of analytical calculations.

## Alternatives

### A — Keep AnalysisRun Globally Visible

**Advantages**
- no persistence migration;
- no application changes;
- simplest compatibility model.

**Trade-offs**
- analysis results from one user remain visible to other users;
- inconsistent with the ownership boundary already established for scheduled workflows;
- prevents meaningful user-scoped run history.

**Assessment:** Not sufficient once analysis is a multi-user capability.

### B — Add One Optional Owner User ID to AnalysisRun

**Advantages**
- matches the existing single-owner workflow model;
- minimal durable schema change;
- supports user-owned and system/global legacy runs;
- ownership can be enforced by the existing authorization identity.

**Trade-offs**
- requires migration and query changes;
- requires explicit behavior for legacy/global runs;
- market-wide application capability must receive owner context.

**Assessment:** Preferred candidate.

### C — Separate AnalysisRun ACL / Sharing Store

**Advantages**
- future sharing and collaboration can be represented directly;
- multiple principals can access one run.

**Trade-offs**
- introduces a second authorization source of truth;
- substantially expands product/security scope;
- unnecessary before sharing is a requirement.

**Assessment:** Deferred.

## Open Questions

1. **Owner identity:** Should ownership use the existing immutable user UUID?
2. **Legacy runs:** Should pre-M54 runs become system/global and operator-only, or remain globally visible?
3. **Operator visibility:** Should the operator see all user-owned runs as well as system/global runs?
4. **System-created runs:** Should scheduled market analysis use a dedicated system owner or remain owner-null/global?
5. **Creation boundary:** Should RunMarketAnalysis require an owner ID, or accept an optional owner for system execution?
6. **Read authorization:** Should ownership filtering happen inside AnalysisRunStore or only in application capabilities?
7. **API behavior:** Should unauthorized run IDs return 404 to avoid resource enumeration?
8. **Dashboard:** Should inaccessible runs be indistinguishable from missing runs?
9. **Backward compatibility:** How should existing API clients behave when ownership metadata is present but not exposed?
10. **Snapshot access:** Should ownership be enforced only through AnalysisRun reads, leaving existing stock-history access unchanged?

## Proposed Invariants

1. Every new user-created AnalysisRun has exactly one owner UUID.
2. System/global runs have an explicit system/global ownership state and are not treated as arbitrary user-owned data.
3. Ownership is immutable after run creation.
4. Users cannot read another user's AnalysisRun or its correlated outcomes/snapshots through run-scoped capabilities.
5. Operators retain visibility according to the existing operator authorization model.
6. Authorization is enforced before run detail or outcome data is returned.
7. Run ownership survives process restart.
8. Ownership does not affect analytical results, retry semantics, or outcome states.
9. React never implements ownership filtering.
10. Legacy runs are handled explicitly; no owner is inferred from historical data.
11. The existing M53 outcome-completeness contract remains unchanged inside an authorized run.
12. The system does not introduce sharing/ACL semantics in this milestone.

## TDD Acceptance Shape

- new user-owned run stores its owner UUID;
- owner survives SQLite restart;
- user can read own run;
- user cannot read another user's run;
- unauthorized run access returns the selected non-enumerating API response;
- operator can read user-owned runs if that decision is accepted;
- system/global scheduled runs remain readable according to the accepted operator boundary;
- legacy runs remain readable according to the accepted migration rule;
- list queries return only authorized runs;
- M53 outcomes remain visible for authorized runs;
- ownership cannot be changed after creation;
- existing analysis calculations and retry behavior remain unchanged.

## Accepted Decisions

### 1. Owner Identity

Ownership uses the existing immutable application user UUID. No username, bearer credential, or mutable profile field is stored on AnalysisRun.

### 2. Legacy Runs

All AnalysisRun records created before M54 are treated as **system/global** records.

No owner is inferred from historical timestamps, authenticated access, workflow correlation, or other indirect evidence.

Legacy/global runs remain available only through the operator visibility boundary.

### 3. Operator Visibility

The existing operator authorization model may read all AnalysisRuns, including user-owned and system/global runs.

Regular users may read only runs owned by their authenticated user UUID.

This preserves the existing operational operator role without creating a new role model.

### 4. System-Created Runs

System-created/scheduled market analysis remains **system/global** with no user owner UUID.

Scheduled workflow ownership and AnalysisRun ownership remain separate concerns. A future requirement to attribute a scheduled run to a user requires a separate decision.

### 5. Creation Boundary

`RunMarketAnalysis.execute` accepts an optional `owner_user_id`.

- authenticated user-triggered execution supplies the authenticated user's UUID;
- system/scheduled execution supplies `None`, producing a system/global run.

Ownership is assigned once at creation and is immutable.

### 6. Read Authorization

`AnalysisRunStore` supports owner-aware persistence/query primitives, but authorization policy remains in application capabilities.

The store does not decide whether a caller is an operator. `GetAnalysisRun` and `ListAnalysisRuns` receive the authenticated identity/authorization context and request either the user's own runs or the operator's all-runs view.

This keeps storage reusable and prevents React/API transport code from reconstructing ownership semantics.

### 7. API Behavior

A non-operator requesting another user's run receives **404 Not Found**, the same external result as a missing run.

This prevents resource enumeration through run identifiers.

List endpoints return only runs visible to the authenticated identity; unauthorized runs are absent rather than represented as filtered-out error records.

### 8. Dashboard and Snapshot Access

The dashboard treats an inaccessible run as missing and does not implement ownership filtering itself.

Run-scoped outcomes and correlated snapshots are accessible only through an authorized AnalysisRun capability.

Existing standalone stock-history access is unchanged in M54; ownership of an AnalysisRun does not implicitly change the ownership model of unrelated historical snapshots.

### 9. Backward Compatibility

Existing API response shapes do not expose owner metadata in M54 unless already required by the established contract.

Ownership is an authorization concern, not a new dashboard display concern.

### 10. Sharing

No ACL, sharing, delegation, team ownership, or multi-owner semantics are introduced.

## Design Gate Decision

**Status: Accepted — implementation is authorized for the M54 MVP defined here.**

The implementation boundary is:

```
AuthenticatedIdentity
        ↓
RunMarketAnalysis(owner_user_id?)
        ↓
AnalysisRun(owner_user_id?)
        ↓
AnalysisRunStore
        ↓
GetAnalysisRun / ListAnalysisRuns
        ↓
API
        ↓
Dashboard
```

The owner field is immutable authorization metadata. It does not affect analytical calculations, retries, execution states, or per-stock outcomes.

## TDD Acceptance Criteria

- new user-owned runs persist the authenticated user UUID;
- ownership survives SQLite restart;
- a user can read their own run;
- a user cannot read another user's run;
- unauthorized run detail returns 404;
- list queries return only authorized runs;
- operator visibility includes user-owned and system/global runs;
- scheduled/system-created runs remain system/global;
- legacy pre-M54 runs remain system/global and operator-only;
- ownership cannot be changed after creation;
- M53 outcomes remain unchanged for authorized runs;
- existing analysis calculations and retry behavior remain unchanged.

## Revisit Conditions

Revisit this gate if:

- organizations or team ownership become requirements;
- run sharing is required;
- delegated analysis becomes a requirement;
- scheduled system runs need user attribution rather than system ownership;
- analysis snapshots become independently shareable resources.
