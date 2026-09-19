# DEC-097 — M38 Multi-User Identity & Ownership Design Gate

**Status:** Proposed  
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

## 8. Open Decisions

The following must be resolved before implementation:

1. **User identity source:** application-local, external provider, or hybrid.
2. **User identifier:** immutable internal UUID versus externally supplied identifier.
3. **Ownership model:** direct user ownership versus an intermediate principal/resource-owner abstraction.
4. **Existing data migration:** how current operator-owned analytical/workflow data is classified during migration.
5. **Authorization semantics:** whether ownership is the only authorization rule or whether roles are introduced with users.
6. **Credential/session model:** bearer tokens, sessions, short-lived access tokens, or provider-issued claims.
7. **User lifecycle:** creation, disablement, deletion, and recovery semantics.
8. **API behavior:** distinction between missing resources and resources owned by another user.
9. **Persistence boundary:** which records become user-scoped and which remain global/system-scoped.
10. **Compatibility:** how existing non-user-aware application capabilities evolve without duplicating authorization logic.
11. **Testing:** deterministic identity fixtures and ownership isolation tests.
12. **Migration path:** whether M37 remains temporarily available during rollout.

## 9. Required Invariants

Before implementation is authorized:

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

**Status: Proposed — implementation is not authorized by this document yet.**

The next step is to resolve the open decisions and record the accepted architecture before implementing multi-user identity or ownership.

## 12. Revisit Conditions

Revisit this gate if the product remains permanently single-operator, if an external identity requirement becomes mandatory, or if a concrete user-owned feature changes the ownership model.
