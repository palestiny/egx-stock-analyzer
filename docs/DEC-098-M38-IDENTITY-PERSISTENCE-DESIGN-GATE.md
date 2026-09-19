# DEC-098 — M38 Identity Persistence & Capability Migration Design Gate

**Status:** Proposed  
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

Introduce a UserRepository application contract and dedicated infrastructure implementation using the existing SQLite deployment, with separate tables and mapping code.

**Trade-offs:** adds a small component, but preserves identity/analytical boundaries and keeps the database technology unchanged.

### C — External identity persistence

Delegate durable identity records to an external provider.

**Trade-offs:** mature lifecycle, but introduces an external dependency prematurely and does not remove the need for local ownership persistence.

## 6. Proposed Direction

**Candidate: B — dedicated identity persistence boundary on the existing SQLite deployment.**

Authentication adapters remain responsible for credentials/tokens. The user repository owns identity/lifecycle records. Analytical persistence remains responsible for analytical data.

No password, token, or provider-specific credential material is persisted by this slice.

## 7. Concrete Capability Migration

The first user-owned capability should be the smallest existing or newly introduced durable application resource that can establish ownership without retrofitting historical analytical records.

It must explicitly define:

- owner reference;
- global/system classification;
- create/read authorization;
- cross-user access;
- reload behavior;
- compatibility behavior for legacy records.

Existing historical analytical/workflow records must not be silently reassigned to a user.

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

## 11. Open Questions

These require explicit resolution before implementation:

1. Which concrete existing or newly introduced small application resource is the first user-owned capability?
2. Should global resources use owner_user_id = NULL or an explicit ownership classification?
3. Should disabled/deleted users retain historical ownership metadata while being denied active access?
4. What exact bootstrap/migration operation creates the designated legacy/system user?
5. Should lifecycle and ownership-resource writes share one transaction when both change together?
6. What compatibility behavior should existing APIs expose while the first user-owned capability is migrated?

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

**Status: Proposed — implementation is not authorized by this document yet.**

The next step is to resolve the open questions and explicitly accept the persistence/migration boundary before production changes are made.

## 14. Revisit Conditions

Revisit if the first user-owned capability requires teams, delegated access, organization ownership, external identity as a hard dependency, or a materially different persistence model.
