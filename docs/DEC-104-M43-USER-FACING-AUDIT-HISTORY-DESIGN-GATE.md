# DEC-104 — M43 User-Facing Audit History Design Gate

**Status:** Accepted  
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

## 7. Accepted Decisions

### 7.1 Visibility rule

M43 adopts **target-only visibility**.

An authenticated user may see an audit event only when target_user_id equals the authenticated user's immutable user_id.

This is deliberately narrower than actor-or-target visibility. The current M41 self-service operation (credential_rotated) already targets the authenticated user, while operator actions concerning the user are also target-scoped. Target-only visibility prevents a future action performed by a user against another identity from becoming an implicit cross-user history channel.

### 7.2 Operator actions

Operator actions targeting the authenticated user's account are visible.

This includes account creation, lifecycle changes, and operator credential rotation when the target is the authenticated user.

Operator actions concerning unrelated users are never visible through the user-facing capability.

### 7.3 Actor representation

The user-facing read model does not expose another user's UUID.

For events targeting the authenticated user:

- actor is represented as self when actor_user_id equals authenticated_user_id;
- actor is represented as operator when the actor is a different identity with operator permission;
- no raw actor UUID is exposed.

This preserves useful context without turning the personal history into an identity-enumeration surface.

### 7.4 Target representation

The user-facing read model represents the target as self.

The authenticated user's UUID is not required in the user-facing history because the endpoint is already scoped to that identity.

No unrelated target UUID can appear.

### 7.5 User-visible action allowlist

The MVP exposes only M41 management actions that directly concern the authenticated user's account:

- user_created;
- user_active;
- user_disabled;
- user_deleted;
- credential_rotated;
- credential_rotated_by_operator.

The application capability filters by target identity first and applies this allowlist explicitly. Unknown or future audit actions are not exposed by default.

### 7.6 Outcome

Both successful and failed events are permitted by the read model.

The current M41 implementation records successful management events only, so the initial observable history will contain successful events. If failed audit events are introduced later, they remain subject to the same target-only visibility and action allowlist.

### 7.7 Filters

The user-facing MVP supports only safe filters that cannot select unrelated identities:

- action;
- outcome;
- UTC from time, inclusive;
- UTC to time, exclusive.

Actor and target UUID filters from M42 are not exposed to users.

The application capability always supplies the authenticated target identity itself.

### 7.8 Pagination and ordering

M43 reuses M42's bounded pagination contract:

- default page size: 50;
- maximum page size: 100;
- invalid non-positive or over-maximum limits are rejected;
- deterministic order remains occurred_at DESC, audit_id DESC.

The user capability does not load the full audit table.

### 7.9 Deleted users

Deletion remains a lifecycle transition and does not erase audit records.

A DELETED user cannot authenticate again under the existing M41 lifecycle semantics, so their personal history is no longer retrievable through the authenticated-user endpoint after deletion. Operators retain the M42 historical audit view.

No historical audit record is reassigned or rewritten.

### 7.10 API shape

M43 uses a dedicated authenticated endpoint:

GET /api/v1/users/me/audit

The endpoint maps to a dedicated user-facing application read capability over ManagementAuditStore.

M42's operator endpoint and application capability remain unchanged.

### 7.11 Dashboard

The existing authenticated user dashboard receives a read-only personal audit-history panel.

The panel exposes:

- event action;
- outcome;
- relative actor label (self / operator);
- UTC event time;
- bounded pagination;
- loading, empty, unavailable, and error states.

The dashboard does not implement visibility, filtering, authorization, ordering, or identity redaction.

### 7.12 Authorization and isolation tests

The implementation must prove at application and API boundaries that:

- an authenticated user receives only events targeting that user;
- events targeting another user are excluded even when the authenticated user is the actor;
- operator audit reporting remains unchanged;
- missing/invalid authentication returns 401;
- authenticated access to the endpoint does not require operator permission;
- deleted identities cannot bypass lifecycle authentication;
- actor/target UUIDs and credential material are not leaked in the user-facing read model.


## 8. Accepted Invariants

1. A user can never retrieve another user's private audit history.
2. Authorization and target scoping are decided by the application capability, not the dashboard.
3. Raw credentials and credential hashes never appear in the user read model.
4. M42 operator visibility remains unchanged.
5. Existing M41 audit-write records remain immutable.
6. Ordering remains deterministic.
7. Pagination remains bounded.
8. Deleted identities remain historically attributable in durable audit storage without reassignment.
9. User-facing history is read-only.
10. Unknown audit actions are not exposed by default.
11. Actor/target UUIDs for unrelated identities never appear in the user-facing read model.
12. Analytical modules remain independent of audit history.

## 9. TDD Acceptance Shape

After acceptance, tests should cover at least:

- empty history;
- own-target event visibility;
- self-performed credential event visibility;
- operator action visibility when the authenticated user is the target;
- unrelated-user isolation;
- deleted-user historical behavior;
- action/outcome redaction;
- filters;
- deterministic ordering;
- bounded pagination;
- API 401 semantics;
- authenticated non-operator access succeeds without requiring operator permission;
- dashboard loading/empty/error states;
- regression protection for M42 operator reporting.

## 10. Design Gate Decision

**Status: Accepted — implementation is authorized for the M43 MVP defined here.**

The implementation boundary is:

```
AuthenticatedIdentity
        ↓
GetUserAuditHistory
        ↓
ManagementAuditStore
        ↓
SQLite
```

If exposed through HTTP:

```
Authenticated Dashboard
        ↓
GET /api/v1/users/me/audit
        ↓
GetUserAuditHistory
        ↓
ManagementAuditStore
```

M43 adds a user-scoped read capability only. It does not change M41 audit writes, M42 operator reporting, lifecycle semantics, credentials, or the authorization model.

## 11. Revisit Conditions

Revisit this gate if:

- organizations or delegated administration are introduced;
- audit requirements become compliance-driven;
- a dedicated security/audit permission model is introduced;
- user-facing security history is no longer required;
- real-time security-event visibility becomes necessary.
