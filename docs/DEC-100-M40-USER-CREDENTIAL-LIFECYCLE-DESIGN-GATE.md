# DEC-100 — M40 User Credential & Session Lifecycle Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M40

## 1. Purpose

M39 established a controlled-deployment authentication adapter: configured per-user bearer credentials resolve to the existing immutable application user identity, and scheduled workflow read/recovery now enforces ownership.

That boundary is intentionally not a complete user-facing authentication system.

M40 must define how user credentials are provisioned, rotated, revoked, and represented in a user-facing session without moving authentication concerns into domain entities or weakening the M38 ownership boundary.

## 2. Problem

The current `EGX_USER_TOKENS` configuration is appropriate for a controlled deployment but has operational limits:

- credential provisioning requires deployment/configuration changes;
- rotation/revocation is coupled to configuration reload/restart;
- the dashboard has no user login/session contract;
- credentials are not represented as durable authentication state;
- there is no user-facing credential lifecycle.

The next design must solve the lifecycle problem without prematurely coupling the application to a specific commercial identity provider.

## 3. In Scope

- credential lifecycle boundary;
- authentication-session boundary;
- provisioning and revocation ownership;
- password/token handling policy if application-managed credentials are selected;
- replacement of the M39 configuration adapter;
- frontend/API session contract;
- preservation of `AuthenticatedIdentity`;
- preservation of M38 ownership authorization;
- migration compatibility with M39 operator/user credentials;
- deterministic 401/403/404 semantics;
- tests and migration strategy.

## 4. Out of Scope

- organizations/teams;
- billing;
- role-management UI;
- MFA/SSO implementation unless explicitly selected by the design;
- delegated access;
- trading authorization;
- notification preferences;
- AI authorization policy;
- distributed authorization policy engines.

## 5. Current Boundary

```
HTTP Request
    ↓
M39 Configured Bearer Authentication Adapter
    ↓
AuthenticatedIdentity
    ↓
Ownership Authorization
    ↓
User-Owned Capability
```

M40 should preserve the application-facing identity and ownership contracts while replacing or extending only the transport/authentication lifecycle boundary.

## 6. Alternatives

### A — Durable Application-Managed Credentials + Sessions

Store credential metadata and securely derived credential verifiers in the application persistence boundary. Issue a server-recognized session after authentication.

**Advantages**
- full provisioning/revocation control;
- no external identity-provider dependency;
- immediate lifecycle changes;
- natural dashboard login model.

**Costs**
- password/token security becomes an application responsibility;
- session persistence and expiration must be designed;
- credential recovery/reset is additional scope.

### B — External Identity Provider Adapter

Delegate authentication to an external OIDC/OAuth2 identity provider and map provider subjects to internal user UUIDs.

**Advantages**
- authentication security/lifecycle is delegated;
- standard login/session flows;
- easier future MFA/SSO.

**Costs**
- external dependency and operational configuration;
- provider selection becomes a product/infrastructure decision;
- local development/testing needs an adapter strategy.

### C — Extend M39 Configuration Credentials

Keep credentials deployment-managed and add a thin dashboard token-entry flow.

**Advantages**
- minimal implementation;
- preserves current architecture;
- no credential database.

**Costs**
- not a real user lifecycle;
- provisioning remains an operator task;
- poor fit for a multi-user product;
- rotation/revocation remains deployment-coupled.

## 7. Trade-Offs

M40 must explicitly distinguish authentication lifecycle from authorization.

The selected design must keep:

- `AuthenticatedIdentity` as the application identity contract;
- ownership checks in the application authorization boundary;
- raw credentials outside domain entities;
- provider-specific authentication details outside application capabilities.

A design that changes the identity contract merely to accommodate one authentication provider is not acceptable.

## 8. Open Decisions

1. Should M40 choose durable application-managed credentials or an external identity-provider adapter?
2. If application-managed, should the first credential be password-based, token-based, or both?
3. What session model is required: server-side session, signed stateless session, or continued bearer-token transport?
4. What are the explicit expiration, revocation, and rotation semantics?
5. How are initial users provisioned?
6. How does M39 configuration authentication coexist during migration?
7. Is frontend login part of M40 or a separate milestone after the backend lifecycle boundary?
8. Which currently operator-only capabilities become user-owned first after the authentication lifecycle is established?

## 9. Required Invariants

- authenticated identity remains an internal UUID-backed `AuthenticatedIdentity`;
- raw credentials never enter domain entities;
- disabled/deleted users cannot establish authenticated identity;
- authorization remains independent from authentication transport;
- user A cannot access user B's owned resources;
- global resources require explicit global/operator authorization;
- M39 credentials remain usable until an explicit migration boundary is reached;
- authentication failure remains 401;
- authorization failure remains 403;
- missing resources remain 404.

## 10. TDD Acceptance Shape

Before implementation is authorized, tests must cover:

- credential provisioning;
- valid authentication;
- invalid authentication;
- disabled/deleted lifecycle rejection;
- credential rotation;
- credential revocation;
- session expiration if sessions are selected;
- migration from M39 configured credentials;
- identity propagation into an existing user-owned capability;
- owner/non-owner authorization;
- global/operator authorization;
- no raw credential leakage;
- adapter replacement without ownership-rule changes.

## 11. Design Gate Rule

M40 implementation is **not authorized by this document yet**.

The next step is to resolve the open decisions, record the accepted choice in this document and `docs/DECISION_LOG.md`, then implement through TDD RED → GREEN on a separate implementation branch.
