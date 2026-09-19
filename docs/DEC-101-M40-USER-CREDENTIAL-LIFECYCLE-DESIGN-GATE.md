# DEC-101 — M40 User Credential & Session Lifecycle Design Gate

**Status:** Accepted  
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

## 8. Accepted Decisions

### 1. Credential Model

M40 uses **durable application-managed opaque bearer credentials** mapped to the existing internal user UUID.

The credential record is infrastructure/application state, not a domain entity. Raw credential values are never persisted, logged, or returned after the provisioning operation.

A credential is represented durably by:
- credential ID;
- owner user UUID;
- one-way credential verifier;
- lifecycle state;
- creation timestamp;
- optional revocation timestamp;
- optional replacement/revocation metadata.

### 2. Passwords and External Identity Providers

M40 does **not** introduce local passwords, password reset flows, MFA, SSO, or a commercial identity provider.

This keeps the accepted M39 bearer transport while adding durable lifecycle control. An external OIDC/OAuth2 adapter remains replaceable future infrastructure and does not alter the application identity or ownership authorization boundary.

### 3. Session Model

The M40 MVP continues the existing bearer transport rather than introducing a second server-side session system.

The browser session is represented by the current frontend sessionStorage credential. The server remains authoritative by resolving the presented credential against durable credential state on every protected request.

### 4. Expiration, Revocation, and Rotation

Credentials do not expire automatically in the M40 MVP.

A credential can be ACTIVE, REVOKED, or REPLACED. Rotation creates a new credential and invalidates the old credential as one application-level operation.

User lifecycle remains authoritative: DISABLED and DELETED users cannot authenticate even when an owned credential is still marked ACTIVE.

### 5. Provisioning

Credential provisioning is an explicit application capability intended for controlled operator/development tooling, not a public self-service endpoint.

The provisioning operation creates credential metadata, returns the raw credential exactly once, and never makes the raw value retrievable later.

Initial user creation remains behind the existing controlled application/user-store boundary; M40 does not add a public registration flow.

### 6. M39 Migration

M39 configured bearer credentials remain supported during the M40 migration boundary.

Durable credentials and M39 configured credentials resolve through the same application identity contract. M39 remains a compatibility adapter and may be removed only through a separate explicit decision.

No automatic copying of raw M39 credentials into durable storage is permitted.

### 7. Frontend Scope

The M40 frontend login/session UX implemented under DEC-100 remains valid. It accepts a bearer credential, stores it only for the browser session, validates it through GET /api/v1/auth/me, and clears it on explicit logout or HTTP 401.

Credential lifecycle work does not expose raw credentials through the identity endpoint.

### 8. Authorization and Identity

AuthenticatedIdentity remains the application identity contract.

Authentication resolves a credential to the internal UUID; authorization remains centralized in the existing application boundary. Owner/non-owner and global/operator semantics remain unchanged.

### 9. Storage and Security Boundary

Credential persistence uses a dedicated CredentialStore boundary backed by the existing SQLite deployment.

Credential verifiers use a one-way cryptographic derivation suitable for secret verification. Raw bearer credentials are excluded from domain entities, API response models, logs, and durable persistence.

The first implementation should prefer standard-library primitives where they provide an appropriate secret-verification construction, avoiding unnecessary dependency expansion.

## 10. Required Invariants

- authenticated identity remains an internal UUID-backed AuthenticatedIdentity;
- raw credentials never enter domain entities or durable storage;
- raw credentials are returned only once by provisioning/rotation;
- disabled/deleted users cannot authenticate;
- revoked/replaced credentials cannot authenticate;
- authorization remains independent from authentication transport;
- user A cannot access user B's owned resources;
- global resources require explicit global/operator authorization;
- M39 credentials remain usable until the explicit compatibility removal boundary;
- authentication failure remains 401;
- authorization failure remains 403;
- missing resources remain 404;
- credential lifecycle operations do not change ownership semantics.

## 11. TDD Acceptance Shape

Before implementation, tests must cover:
- credential provisioning and one-time raw credential return;
- valid authentication;
- invalid authentication;
- disabled/deleted user rejection;
- credential revocation;
- credential rotation and invalidation of the previous credential;
- persistence/reload of credential state;
- M39 configured-credential compatibility;
- identity propagation into an existing user-owned capability;
- owner/non-owner authorization;
- global/operator authorization;
- no raw credential leakage into persisted records or API responses;
- adapter replacement without ownership-rule changes.

## 12. Design Gate Decision

**Status: Accepted — implementation is authorized for the M40 credential-lifecycle MVP defined here.**

The implementation boundary is:

Credential Provisioning / Rotation / Revocation
                  ↓
            CredentialStore
                  ↓
        Authentication Adapter
                  ↓
        AuthenticatedIdentity
                  ↓
        Authorization Boundary
                  ↓
        User-Owned Capability

The credential lifecycle layer owns credential secrets and lifecycle state. It does not own user identity, resource ownership, analytical domain rules, or authorization policy.

## 11. Design Gate Rule

M40 implementation is **not authorized by this document yet**.

The next step is to resolve the open decisions, record the accepted choice in this document and `docs/DECISION_LOG.md`, then implement through TDD RED → GREEN on a separate implementation branch.
