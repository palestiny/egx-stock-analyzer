# DEC-098 — M38 Identity Persistence & Capability Migration Design Gate

**Status:** Accepted  
**Date:** 2026-09-19  
**Milestone:** M38 — Multi-User Identity & Ownership

## 1. Context

The M38 foundation slice is complete: immutable application user lifecycle, application identity, explicit ownership authorization, and deterministic M37 legacy mapping are implemented.

The remaining M38 scope is persistence/reload and migration of a concrete user-owned capability.

## 2. Problem

Without durable identity state, users and lifecycle state cannot survive process restart, ownership cannot be reliably attached to durable resources, and the M37 compatibility mapping cannot be a persistent migration boundary.

A concrete user-owned capability also needs to prove ownership after reload without moving authentication concerns into analytical domain entities.

## 3. Desired Outcome

This slice should establish:

1. a durable application-user repository boundary;
2. deterministic user creation/reconstitution;
3. lifecycle persistence and reload;
4. deterministic legacy operator identity mapping;
5. one concrete user-owned capability behind the authorization boundary;
6. ownership surviving restart;
7. transport 401/403/404 semantics remaining outside ownership logic;
8. no credentials/tokens entering domain entities.

## 4. Scope

### In scope

- application-user persistence contract;
- user repository implementation;
- lifecycle persistence;
- legacy/system operator mapping persistence;
- owner-reference persistence for one capability;
- authorization after reload;
- SQLite integration tests;
- deterministic migration behavior.

### Out of scope

- passwords or credential storage;
- JWT/session implementation;
- external identity provider integration;
- MFA/SSO;
- organizations/teams;
- role management;
- bulk migration of all historical resources;
- redesign of analytical persistence;
- notification preference product design.

## 5. Persistence Alternatives

### A — Extend analytical SQLite persistence

Store users beside analytical data.

**Trade-offs:** reuses infrastructure, but risks coupling identity lifecycle to analytical persistence and serialization.

### B — Dedicated identity persistence boundary on existing SQLite

Introduce a UserStore application contract and dedicated infrastructure implementation using the existing SQLite deployment, with a separate `users` table and explicit mapper.

**Trade-offs:** adds a small component, but preserves identity/analytical boundaries and keeps the database technology unchanged. Ownership fields remain on the concrete user-owned capability rather than being folded into the user persistence schema.

### C — External identity persistence

Delegate durable identity records to an external provider.

**Trade-offs:** mature lifecycle, but introduces an external dependency prematurely and does not remove the need for local ownership persistence.

## 6. Proposed Direction

**Candidate: B — dedicated identity persistence boundary on the existing SQLite deployment.**

Authentication adapters remain responsible for credentials/tokens. The user repository owns identity/lifecycle records. Analytical persistence remains responsible for analytical data.

No password, token, or provider-specific credential material is persisted by this slice.

## 7. Concrete Capability Migration

The first user-owned capability is the existing **ScheduledWorkflowExecution** application resource.

This is selected because it is already a durable application resource with a repository boundary, lifecycle semantics, API visibility, and dashboard visibility. It provides a concrete ownership proof without modifying analytical domain entities.

Ownership is represented by:

`owner_user_id: UUID | None`

For this capability, `NULL` means **system/global legacy ownership**. A non-null value must reference an existing application user.

The migration does not invent ownership for historical executions. Existing persisted scheduled-workflow executions remain system/global (`owner_user_id = NULL`) until a separate explicit migration operation is designed.

The migrated capability must explicitly define:

- owner reference;
- system/global legacy classification;
- create/read authorization;
- cross-user access;
- reload behavior;
- compatibility behavior for legacy records.

New user-owned scheduled-workflow executions require an active authenticated user. Legacy operator access remains compatible only with system/global records and does not implicitly become ownership of another user's records.

## 8. Legacy M37 Mapping

The M37 operator token maps deterministically to one designated legacy/system identity.

Persistence must guarantee:

- repeated startup resolves to the same internal UUID;
- no duplicate legacy identity is created;
- existing analytical/workflow records remain system-owned legacy data;
- compatibility authentication does not bypass ownership checks.

## 9. Persistence Semantics

Required behavior:

- create user;
- load by internal UUID;
- update lifecycle state;
- reload using a new repository instance;
- deterministic legacy identity lookup/creation;
- owner reference survives reload;
- missing owner/resource is explicit.

Corrupt or unsupported identity records fail explicitly rather than silently generating a replacement identity.

## 10. Authorization Boundary

The application authorization boundary remains the single owner of ownership checks:

    AuthenticatedIdentity
            ↓
    Authorization Boundary
            ↓
    User-Owned Capability
            ↓
    Repository / Persistence

Controllers and dashboard code must not implement ownership comparisons. Analytical domain services remain identity-agnostic.

## 11. Resolved Decisions

1. **First user-owned capability:** `ScheduledWorkflowExecution` is the first migrated durable resource.
2. **Global/system classification:** `owner_user_id = NULL` means system/global legacy ownership for this capability. Non-null means explicit user ownership. No arbitrary user is used as a global owner.
3. **Disabled/deleted users:** ownership metadata remains persisted for historical attribution, but disabled/deleted identities cannot access protected owned resources.
4. **Legacy bootstrap:** the existing deterministic `LEGACY_OPERATOR_USER_ID` is materialized idempotently in the users store as the designated compatibility identity. Existing historical scheduled-workflow records are not reassigned to it; they remain system/global.
5. **Transactions:** user lifecycle writes and scheduled-workflow ownership writes remain repository-local atomic operations in this slice. A cross-repository transaction is not introduced because no current command changes both aggregates atomically. If a future command must change both, a unit-of-work/transaction design gate is required.
6. **Compatibility:** existing legacy APIs continue to expose system/global scheduled-workflow records through the M37 operator path. New user-owned scheduled-workflow operations require an active authenticated identity and must pass the ownership authorization boundary. No endpoint may infer ownership from URL shape or dashboard state.

## 12. TDD Acceptance Shape

At minimum:

- user create → persist → reload;
- lifecycle state survives reload;
- legacy mapping is deterministic across repeated initialization;
- two users can own separate resources;
- user A can access user A's resource;
- user A receives forbidden behavior for user B's resource;
- missing resource remains not-found;
- disabled/deleted user cannot access protected owned resource;
- ownership survives repository/application restart;
- alternate API paths cannot bypass ownership;
- no raw credential/token reaches the domain model;
- historical analytical records remain system-owned legacy data.

## 13. Design Gate Decision

**Status: Accepted — implementation is authorized for the M38 persistence/capability-migration slice defined here.**

The implementation boundary is:

```
Authentication Adapter
        ↓
AuthenticatedIdentity
        ↓
Ownership Authorization Boundary
        ↓
ScheduledWorkflowExecution Capability
        ↓
UserStore + ScheduledWorkflowExecutionStore
        ↓
SQLite
```

Identity persistence is separate from analytical persistence. Historical scheduled-workflow executions remain system/global unless an explicit future migration assigns ownership.

## 14. Revisit Conditions

Revisit if the first user-owned capability requires teams, delegated access, organization ownership, external identity as a hard dependency, or a materially different persistence model.
