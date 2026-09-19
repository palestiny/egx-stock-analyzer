# DEC-104 — M43 User-Facing Audit History Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M43

## 1. Purpose

M42 completed operator-only management-audit reporting over the durable M41 audit boundary.

The next potential capability is controlled visibility for authenticated users over the subset of management events they are authorized to see. This gate defines that problem before any user-facing audit-history behavior is implemented.

M43 must not weaken the operator-only M42 capability or move authorization rules into React/API transport code.

## 2. Problem

M42 intentionally limits audit reporting to operators. In a multi-user system, some users may eventually need visibility into security-sensitive activity concerning their own identity, such as credential rotation or account lifecycle changes.

A user-facing history capability must answer:

- which events can a user see;
- how actor/target identities are represented;
- whether users can see events they performed;
- whether users can see events performed about them;
- which action/outcome metadata is safe to expose;
- whether operator actions concerning another user are visible to that target;
- how deleted identities remain represented;
- how pagination and filtering differ from operator reporting.

## 3. In Scope

- authenticated user audit-history application capability;
- explicit ownership/visibility rules;
- read-model redaction;
- deterministic ordering;
- bounded pagination;
- safe filters;
- API boundary;
- dashboard presentation boundary;
- authorization and isolation tests.

## 4. Explicitly Out of Scope

- changing M41 audit-write behavior;
- changing M42 operator audit reporting;
- new roles/organizations;
- audit retention/deletion;
- SIEM/log shipping;
- real-time streaming;
- audit analytics;
- notification/alerting based on audit events;
- public audit access;
- credential recovery or lifecycle changes.

## 5. Current Boundary

```
AuthenticatedIdentity
        ↓
User Audit History Application Capability
        ↓
ManagementAuditStore
        ↓
SQLite
```

If exposed:

```
React Dashboard
        ↓
HTTP API
        ↓
User Audit History Application Capability
```

The application capability must remain authoritative for visibility and filtering semantics.

## 6. Candidate Alternatives

### A — Target-Only Visibility

A user sees only events whose `target_user_id` equals the authenticated user's ID.

**Trade-offs**

- simplest ownership rule;
- strong isolation;
- omits actions performed by a user that targeted another identity;
- may make the user's own security activity incomplete.

### B — Actor-or-Target Visibility

A user sees events where their ID is either the actor or target.

**Trade-offs**

- provides a broader personal security history;
- requires explicit redaction rules for events involving another user;
- may expose more administrative context than necessary.

### C — Explicit User-Visible Event Classification

Audit events gain a read-side visibility classification determining whether an event is user-visible.

**Trade-offs**

- precise and extensible;
- introduces another semantic dimension;
- existing M41 records would need a deterministic interpretation;
- increases implementation and migration complexity.

## 7. Open Decisions

1. **Visibility rule:** target-only, actor-or-target, or explicit event visibility classification?
2. **Operator actions:** should a user see an operator action performed on their account?
3. **Actor representation:** when another user is the actor, expose UUID only, a stable display identifier, or redact the actor?
4. **Target representation:** should the authenticated user's own UUID be shown, and should unrelated target UUIDs ever appear?
5. **Action allowlist:** which M41 actions are user-visible?
6. **Outcome:** should failed management attempts be visible to the affected user?
7. **Filters:** which filters are safe for users without allowing enumeration of unrelated identities?
8. **Pagination:** reuse M42 page size limits and ordering?
9. **Deleted users:** how should historical records behave when the authenticated identity is later deleted?
10. **API shape:** separate endpoint from operator audit reporting or a shared capability with distinct authorization modes?
11. **Dashboard:** where should user audit history appear without exposing operator-only controls?
12. **Authorization tests:** what cross-user isolation matrix is required before implementation?

## 8. Proposed Invariants

1. A user can never retrieve another user's private audit history.
2. Authorization is decided by the application capability, not the dashboard.
3. Raw credentials and credential hashes never appear in the user read model.
4. M42 operator visibility remains unchanged.
5. Existing M41 audit-write records remain immutable.
6. Ordering remains deterministic.
7. Pagination remains bounded.
8. Deleted identities remain historically attributable without reassigning ownership.
9. Analytical modules remain independent of audit history.
10. User-visible audit reporting is read-only.

## 9. TDD Acceptance Shape

After acceptance, tests should cover at least:

- empty history;
- own-target event visibility;
- own-actor event visibility if accepted;
- operator action visibility if accepted;
- unrelated-user isolation;
- deleted-user historical behavior;
- action/outcome redaction;
- filters;
- deterministic ordering;
- bounded pagination;
- API 401/403 semantics;
- dashboard loading/empty/error states;
- regression protection for M42 operator reporting.

## 10. Design Gate Decision

**Status: Proposed — implementation is not authorized by this document.**

M43 implementation must wait until the visibility, redaction, authorization, API, and dashboard decisions above are explicitly accepted.

## 11. Revisit Conditions

Revisit this gate if:

- organizations or delegated administration are introduced;
- audit requirements become compliance-driven;
- a dedicated security/audit permission model is introduced;
- user-facing security history is no longer required;
- real-time security-event visibility becomes necessary.
