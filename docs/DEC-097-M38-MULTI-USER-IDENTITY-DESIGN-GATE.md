# DEC-097 — M38 Multi-User Identity & Ownership Design Gate

**Status:** Accepted  
**Date:** 2026-09-19  
**Milestone:** M38 — Multi-User Identity & Ownership

## 1. Context

M37 established a single-operator bearer-token security boundary. The application is now authenticated, but the security model intentionally does not identify multiple users or establish ownership of application resources.

If the platform is to evolve from a single trusted operator into a multi-user product, identity and ownership must be designed before adding user-specific dashboards, preferences, watchlists, notification destinations, or other user-owned state.

## 2. Problem

The current boundary answers:

- whether the configured operator token is valid;
- whether the caller has the single operator permission.

It does not answer:

- which user is making the request;
- which resources belong to that user;
- how ownership is persisted;
- how authorization is evaluated against ownership;
- how an existing operator identity migrates to a user identity;
- how user lifecycle and credential management should work.

Adding user-specific behavior without these decisions would risk scattering authorization rules across endpoints, dashboards, and application capabilities.

## 3. Desired Outcome

M38 should define a coherent multi-user identity and ownership architecture that:

1. establishes a stable application identity contract;
2. defines user identity and lifecycle;
3. defines resource ownership semantics;
4. establishes authorization rules for owned resources;
5. preserves domain independence from HTTP/authentication technology;
6. defines migration from the current single-operator boundary;
7. defines credential/session/token responsibilities;
8. defines deterministic testing and local development behavior.

## 4. In Scope

- user identity model;
- authenticated identity representation;
- resource ownership model;
- authorization boundary;
- user lifecycle;
- credential/session/token responsibility;
- migration from M37 operator token;
- application capability dependency direction;
- persistence ownership boundaries;
- API semantics for unauthorized versus forbidden resources;
- deterministic testing strategy.

## 5. Out of Scope

- selecting a commercial identity provider as an implementation;
- social login;
- MFA;
- SSO;
- billing/subscriptions;
- organization/team administration;
- role-management UI;
- trading authorization;
- audit-log product design;
- rate limiting/WAF;
- notification preference product design;
- AI authorization policy.

These may require separate design gates.

## 6. Current Boundary

M37 currently establishes:

```
HTTP
  ↓
Bearer Token Authentication
  ↓
AuthenticatedIdentity(operator)
  ↓
Authorization Boundary
  ↓
Application Capability
  ↓
Domain
```

M38 must evolve this without moving authentication concerns into domain entities.

## 7. Candidate Alternatives

### A. Application-local user identity

Maintain users and ownership in the application's persistence boundary and issue application-managed authentication credentials.

**Advantages**
- full control over identity and ownership semantics;
- deterministic local deployment;
- no mandatory external identity dependency.

**Trade-offs**
- credential lifecycle and security become application responsibilities;
- password/session/token management requires careful design;
- migration and account recovery become product concerns.

### B. External identity provider

Delegate authentication and identity lifecycle to an external identity provider while retaining application-local ownership records.

**Advantages**
- mature authentication lifecycle;
- avoids storing application passwords;
- easier path to federation and SSO.

**Trade-offs**
- external dependency and provider-specific integration;
- configuration and local-development complexity;
- provider migration becomes a future concern.

### C. Hybrid identity boundary

Keep an application-level identity/ownership contract while allowing the authentication adapter to be backed by either local or external authentication.

**Advantages**
- preserves application portability;
- separates identity semantics from authentication mechanism;
- supports gradual migration.

**Trade-offs**
- larger initial boundary;
- requires explicit identity mapping and lifecycle rules.

## 8. Accepted Decisions

### 8.1 Identity Source — Hybrid Application Identity Boundary

M38 adopts the hybrid boundary.

The application owns the stable identity and ownership contracts. Authentication remains an adapter concern and may be backed by the current local mechanism or a future external provider.

This preserves application portability while avoiding coupling user ownership to a specific authentication vendor.

### 8.2 User Identifier — Internal UUID

Each application user has an immutable internal UUID.

External authentication identifiers, if introduced later, are mapped to this internal identity rather than becoming the application's primary identity.

### 8.3 Ownership — Explicit User Ownership

M38 uses direct ownership for user-owned resources:

```
Resource.owner_user_id → User.id
```

An intermediate principal/resource-owner abstraction is deferred because there is no current requirement for teams, organizations, delegated access, or service principals.

System/global resources remain explicitly unowned rather than being assigned to an arbitrary user.

### 8.4 Existing Data Migration

Existing M37 data is classified as **system-owned legacy data** during the first migration.

No historical analytical or workflow record is silently reassigned to a newly created user. User-specific ownership of those records requires an explicit future migration operation.

This preserves existing semantics and avoids inventing ownership from incomplete historical context.

### 8.5 Authorization — Ownership First, Roles Deferred

For M38, authorization is based on:

- authenticated user identity;
- explicit resource ownership;
- explicit system/global access policy.

No general role-management model is introduced yet. The current single-operator permission model is treated as a compatibility policy during migration, not as the long-term multi-user authorization model.

### 8.6 Credential / Session Model — Adapter-Owned Authentication

The application-level contract receives an authenticated application identity, not raw credentials.

The authentication adapter owns credential validation and session/token mechanics.

The M38 implementation does not commit to passwords, browser sessions, JWTs, or a commercial provider as domain/application concepts.

### 8.7 User Lifecycle

M38 defines these lifecycle states:

- ACTIVE — may authenticate and access resources according to authorization policy.
- DISABLED — identity remains persisted but cannot authenticate/access protected user-owned resources.
- DELETED — identity is logically removed from active use while ownership references remain historically attributable.

Physical deletion of user-owned historical records is not part of M38.

Account recovery and credential reset remain authentication-adapter concerns.

### 8.8 API Semantics

For protected user-owned resources:

- unauthenticated request → HTTP 401;
- authenticated request for another user's resource → HTTP 403;
- authenticated request for a non-existent resource → HTTP 404.

The application authorization boundary decides ownership. HTTP maps the resulting application outcomes to transport semantics.

### 8.9 Persistence Boundary

User identity and ownership metadata are persisted separately from analytical domain calculations.

Records that become user-owned must carry an explicit owner reference. Global/system records remain explicitly global.

M38 does not retrofit every existing record immediately; ownership is added as each user-owned capability is migrated.

### 8.10 Compatibility

Existing application capabilities continue to operate behind their current interfaces.

User context is introduced at the application authorization boundary and passed only to capabilities that require ownership decisions. Domain analytical services remain identity-agnostic.

Authorization logic is not duplicated in controllers, dashboard components, or domain entities.

### 8.11 Testing

Tests use deterministic application-user fixtures with stable UUIDs.

The minimum contract includes positive ownership, cross-user isolation, global-resource policy, persistence/reload, disabled/deleted identities, alternate API-path isolation, and authentication-adapter replacement.

### 8.12 M37 Migration Path

M37's single-operator token remains temporarily supported as a compatibility authentication adapter during M38 rollout.

It maps to a designated legacy/system operator identity.

New user-owned capabilities must use the M38 application identity contract. The M37 compatibility path must not grant ownership of another user's resources.

The M37 compatibility path can be removed only through a later explicit migration/completion decision.

## 9. Required Invariants

The accepted design must preserve:

1. Domain analytical rules remain identity-agnostic.
2. Ownership is represented explicitly rather than inferred from HTTP routes.
3. Authorization decisions have one application-level owner.
4. Dashboard code does not implement ownership rules.
5. A user cannot access another user's owned resource through an alternate endpoint.
6. System/global resources are explicitly distinguished from user-owned resources.
7. Existing persisted data has an explicit migration classification.
8. Authentication mechanism remains replaceable behind its adapter boundary.
9. Tests prove ownership isolation, not only authentication success.
10. Migration from M37 does not silently change analytical semantics.

## 10. TDD Acceptance Shape

The accepted design should require tests covering at minimum:

- authenticated user identity reaches protected application capabilities;
- user A can access user A owned resources;
- user A cannot access user B owned resources;
- system/global resources remain explicitly accessible according to policy;
- ownership is preserved across persistence/reload;
- disabled/deleted users cannot access protected resources;
- alternate API paths cannot bypass ownership checks;
- M37 operator-data migration is deterministic;
- authentication mechanism remains outside domain logic.

## 11. Design Gate Decision

**Status: Accepted — implementation is authorized for the M38 MVP defined here.**

The implementation boundary is:

```
HTTP / Authentication Adapter
          ↓
AuthenticatedIdentity
          ↓
Application Authorization Boundary
          ↓
User-Owned Application Capability
          ↓
Domain / Persistence
```

Authentication mechanisms remain replaceable. Ownership is explicit. Domain analytical behavior remains identity-agnostic. M37 remains only as a temporary compatibility authentication path during rollout.

## 12. TDD Acceptance Criteria

Implementation must establish at least:

- authenticated identity reaches a protected application capability;
- user A can access user A owned resources;
- user A receives forbidden behavior for user B owned resources;
- global resources follow an explicit policy;
- ownership survives persistence and reload;
- disabled identities cannot access protected resources;
- deleted identities cannot access protected resources;
- alternate API paths cannot bypass ownership checks;
- legacy M37 operator identity mapping is deterministic;
- raw credentials never reach domain entities;
- authentication adapters can be replaced without changing ownership semantics.

## 13. Revisit Conditions

## 14. Revisit Conditions

Revisit this gate if the product remains permanently single-operator, if an external identity requirement becomes mandatory, or if a concrete user-owned feature changes the ownership model.
