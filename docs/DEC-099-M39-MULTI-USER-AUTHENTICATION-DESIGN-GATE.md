# DEC-099 — M39 Multi-User Authentication & Identity Transport Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M39 — Multi-User Authentication & Identity Transport

## 1. Context

M37 established a single-operator bearer-token authentication boundary.

M38 established durable application users, immutable internal user UUIDs, ownership authorization, and durable ownership for ScheduledWorkflowExecution. The application layer can now distinguish user-owned resources from system/global legacy resources.

The remaining gap is transport-level multi-user identity: protected HTTP requests still authenticate through the M37 operator-token contract, while M38 user identity is currently supplied directly to application capabilities.

## 2. Problem

A durable multi-user ownership model is not sufficient if transport requests cannot establish which application user is making the request.

The next boundary must answer how an incoming request becomes an AuthenticatedIdentity, how multiple users authenticate, how lifecycle state affects authentication, how legacy operator authentication coexists, how API capabilities receive identity, and how 401/403/404 semantics remain separated from ownership rules.

## 3. Desired Outcome

Establish a transport/application identity boundary that allows protected API capabilities to receive an authenticated application identity.

Requirements:
- keep credentials and tokens outside domain entities;
- resolve an authenticated request to an immutable application user identity;
- reject disabled/deleted users;
- preserve M37 legacy operator compatibility during migration;
- pass AuthenticatedIdentity into user-owned application capabilities;
- keep ownership checks in the application authorization boundary;
- preserve HTTP 401/403/404 transport semantics;
- remain replaceable with an external identity provider later.

## 4. Scope

### In scope
- request authentication → AuthenticatedIdentity boundary;
- multi-user identity resolution contract;
- lifecycle checks during authentication;
- compatibility with LEGACY_OPERATOR_USER_ID;
- API composition changes needed to pass identity;
- ownership-scoped access to the first migrated capability;
- deterministic authentication and authorization tests;
- migration/deprecation boundary for M37 operator authentication.

### Explicitly out of scope
- organizations and teams;
- roles beyond the existing operator compatibility permission;
- delegated access;
- MFA/SSO;
- password reset;
- social login;
- authorization policy redesign;
- ownership migration for all historical resources;
- trading permissions;
- notification preference product design;
- frontend user-management product UX;
- distributed session storage.

## 5. Alternatives Considered

### A — Keep one configured operator token and select a user separately

This would authenticate as the operator and identify the user through another request value.

Trade-offs: small implementation change, but it does not provide trustworthy user authentication and creates identity-spoofing risk.

Assessment: Rejected.

### B — Map configured bearer credentials directly to application users

The application keeps a deterministic mapping between configured bearer credentials and internal user IDs.

Trade-offs: simple and deterministic for a controlled deployment, but requires secure credential configuration/rotation and is not a general-purpose identity product.

Assessment: Candidate for the first migration-compatible implementation.

### C — Introduce a replaceable external identity provider adapter

The application delegates authentication to an external IdP and receives a stable subject/user mapping.

Trade-offs: strong long-term identity capabilities and avoids implementing password security, but introduces external infrastructure and integration complexity.

Assessment: Candidate for a later concrete provider integration; the application boundary should remain compatible with it now.

### D — Implement local username/password sessions

Trade-offs: fully self-contained multi-user authentication, but introduces password hashing, credential recovery, session invalidation, CSRF/security concerns, and substantial additional lifecycle state.

Assessment: Deferred unless product requirements explicitly require local account authentication.

## 6. Proposed Boundary

HTTP Request
    ↓
Authentication Adapter
    ↓
AuthenticatedIdentity
    ↓
Application Capability
    ↓
Ownership Authorization Boundary

The resolver returns application identity, not raw credentials. Controllers pass resolved identity to application capabilities and do not compare user IDs against resources themselves.

## 7. Identity Contract

The existing AuthenticatedIdentity remains the application identity model.

The transport boundary may resolve an authenticated active user, the designated legacy operator compatibility identity, or no identity.

The application must not infer ownership from URL parameters, dashboard state, arbitrary request headers, or client-supplied user IDs.

## 8. Legacy Migration Semantics

M37 operator authentication remains temporarily supported.

- legacy operator credentials resolve to LEGACY_OPERATOR_USER_ID;
- legacy operator access remains compatible with system/global workflow records;
- legacy operator credentials must not impersonate an arbitrary user;
- user-owned resources require the corresponding authenticated user identity;
- removal of M37 compatibility requires a separate explicit decision.

## 9. User Lifecycle Semantics

Authentication resolution must consult durable user lifecycle state.

- ACTIVE → authentication may proceed;
- DISABLED → authentication fails;
- DELETED → authentication fails;
- missing user → authentication fails rather than creating an implicit identity.

## 10. API Ownership Semantics

For the first migrated capability:
- authenticated owner → capability may proceed;
- authenticated non-owner → application authorization raises the ownership error;
- system/global legacy resource → only the explicitly supported compatibility identity may access it;
- absent resource → application reports not-found and transport maps it to HTTP 404.

Transport maps authentication failures to 401 and authorization failures to 403.

## 11. TDD Acceptance Shape

- authenticated request resolves to the expected user identity;
- disabled user cannot authenticate;
- deleted user cannot authenticate;
- unknown user cannot authenticate;
- legacy operator resolves deterministically to LEGACY_OPERATOR_USER_ID;
- legacy operator cannot impersonate another user;
- user A can access user A's owned workflow;
- user A cannot access user B's owned workflow;
- system/global legacy workflow remains accessible only through the explicit compatibility path;
- missing resource remains 404;
- authentication failures remain 401;
- authorization failures remain 403;
- no raw token/password reaches application domain entities;
- replacing the authentication adapter does not require changing ownership semantics.

## 12. Accepted Decisions

### 12.1 Concrete Authentication Mechanism

M39 will use **configured per-user bearer credentials** as the first concrete transport adapter.

The application boundary remains adapter-based so an external identity provider can replace this adapter later without changing ownership semantics.

Credentials are configuration/infrastructure data. They are never represented by domain entities and are never passed into application capabilities.

### 12.2 Provisioning, Rotation, and Revocation

M39 will not build a user-management product or password system.

For the first slice, credential-to-user mappings are supplied through deployment configuration and resolved by the authentication adapter. A configured credential maps to one immutable internal user UUID.

The mapping is authoritative for authentication. Changing or removing a mapping revokes that credential after the application's configuration is reloaded/restarted according to the deployment model.

Durable user lifecycle state remains authoritative for whether the mapped user may authenticate.

This is intentionally a controlled-deployment mechanism, not a complete identity-management product. A later identity-provider decision may replace it.

### 12.3 First API/Application Scope

The first migrated user-owned capability is the **scheduled workflow execution read/recovery surface**:

- `GET /api/v1/workflows/executions`
- `POST /api/v1/workflows/executions/{execution_id}/recover`

The application layer receives `AuthenticatedIdentity` and applies the existing ownership authorization boundary.

Other analytical, reporting, notification, and administrative endpoints remain on the M37 operator compatibility path until separate migration decisions are made.

### 12.4 Legacy Operator Compatibility

M37 operator-token compatibility remains supported during M39.

It ends only through a separate explicit decision after all endpoints that depend on operator compatibility have either been migrated to user identity or intentionally remain system/operator-only.

M39 therefore does not introduce a time-based or automatic removal of the legacy credential.

The legacy operator maps only to `LEGACY_OPERATOR_USER_ID` and cannot select or impersonate another user.

### 12.5 Frontend Scope

M39 is **API/application focused**.

The frontend is not required to implement login/session UX in this milestone. Existing dashboard behavior may continue using the compatibility path while the backend identity boundary is established and tested.

A separate frontend authentication design/implementation slice will be required before user-facing login is considered complete.

### 12.6 Identity Lookup Frequency

M39 resolves identity on every authenticated request.

No authentication-result cache is introduced in the first slice.

This keeps lifecycle changes deterministic: disabling or deleting a user is reflected without waiting for a cache expiry.

## 13. Accepted Design Gate Decision

**Status: Accepted — implementation is authorized for the M39 MVP defined here.**

The accepted boundary is:

```
HTTP Request
    ↓
Bearer Authentication Adapter
    ↓
AuthenticatedIdentity
    ↓
Application Capability
    ↓
Ownership Authorization Boundary
    ↓
User-Owned Resource
```

M39 concrete adapter details are infrastructure/configuration concerns. The application contract consumes only `AuthenticatedIdentity`.

### Accepted invariants

- raw credentials never reach domain entities;
- client-supplied user IDs never establish identity;
- ACTIVE users may authenticate;
- DISABLED and DELETED users cannot authenticate;
- unknown mapped users cannot authenticate;
- legacy operator credentials resolve only to `LEGACY_OPERATOR_USER_ID`;
- authentication failure maps to HTTP 401;
- authorization failure maps to HTTP 403;
- missing resources remain HTTP 404;
- ownership checks remain in the application authorization boundary;
- replacing the bearer adapter later does not change ownership semantics;
- identity is resolved on every protected request.

### TDD acceptance criteria

- valid configured user credential resolves to the expected `AuthenticatedIdentity`;
- disabled user credential is rejected;
- deleted user credential is rejected;
- credential mapped to a missing user is rejected;
- legacy operator credential resolves deterministically to `LEGACY_OPERATOR_USER_ID`;
- legacy operator cannot select another user;
- user A can read/recover user A's scheduled workflow execution;
- user A cannot read/recover user B's scheduled workflow execution;
- global/legacy records follow the explicit compatibility path;
- missing workflow execution remains 404;
- invalid/missing credentials remain 401;
- authenticated non-owner remains 403;
- no raw credential reaches domain/application capability contracts;
- replacing the authentication adapter leaves ownership tests unchanged.

## 14. Revisit Conditions

Revisit if an external identity provider becomes mandatory, local credentials become a product requirement, organizations/teams become required, the application becomes a public multi-tenant service, or authentication needs distributed/session semantics.