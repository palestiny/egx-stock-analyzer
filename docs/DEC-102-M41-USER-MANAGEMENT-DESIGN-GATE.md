# DEC-102 — M41 User Management & Credential Administration Design Gate

**Status:** Accepted  
**Date:** 2026-09-19  
**Milestone:** M41

## 1. Purpose

M38 established internal user identity and ownership. M39 established multi-user authentication transport. M40 established durable bearer credential lifecycle and browser session UX.

The remaining product gap is controlled user administration: users and their credentials currently have application/infrastructure capabilities but no defined user-management surface.

M41 should define the boundary for creating, disabling, reactivating, deleting, and administering users and their credentials without moving identity or authorization rules into analytical domain entities.

## 2. Problem

The current system can authenticate existing users and persist credential lifecycle state, but it does not yet define:

- who may create users;
- who may disable or delete users;
- whether users can manage their own credentials;
- how credential replacement is exposed;
- how deleted users affect historical ownership;
- which operations are operator-only versus self-service;
- how these operations are exposed without coupling business identity rules to FastAPI or React.

## 3. In Scope

- user-management application boundary;
- user lifecycle commands;
- credential administration commands;
- operator versus self-service responsibilities;
- API transport boundary;
- frontend UX boundary;
- authorization semantics;
- auditability requirements;
- migration compatibility with M37/M40;
- deterministic tests.

## 4. Explicitly Out of Scope

- organizations/teams;
- billing;
- MFA/SSO;
- external identity providers;
- delegated access;
- trading permissions;
- notification preferences;
- role-management product;
- distributed authorization engines.

## 5. Current Boundary

```
HTTP / Dashboard
      ↓
Authentication
      ↓
AuthenticatedIdentity
      ↓
Application Authorization
      ↓
User / Credential Management Capability
      ↓
UserStore / CredentialStore
```

The domain analytical modules remain identity-agnostic.

## 6. Candidate Alternatives

### A — Operator-Only Administration

Operators create, disable, delete, and rotate credentials for users. End users only consume authenticated application capabilities.

**Trade-offs**
- smallest product surface;
- strongest operational control;
- requires an operator for routine account changes;
- does not provide self-service credential recovery.

### B — Self-Service Credential Administration

Users can rotate/revoke their own credentials while operators retain user lifecycle administration.

**Trade-offs**
- better routine autonomy;
- clearer separation between account administration and credential possession;
- requires careful authorization and UX for credential loss/replacement;
- does not solve initial user provisioning by itself.

### C — Full Self-Service User Management

Users can register, manage their profile, and administer credentials, while operators retain privileged lifecycle controls.

**Trade-offs**
- largest product surface;
- requires registration, recovery, abuse protection, and lifecycle UX;
- closer to a complete identity product;
- substantially expands M41 security and operational scope.

## 7. Accepted Decisions

### 7.1 Administration model

M41 adopts self-service credential administration plus operator-controlled user lifecycle administration.

Users may rotate their own credential. Operators may create users, disable/reactivate users, delete users, and administer credentials for users. Full self-service registration/profile management is deferred.

### 7.2 First-user provisioning

The designated legacy/system operator identity is the bootstrap administrator. Creating the first non-legacy user is an authenticated operator operation.

### 7.3 Credential revocation

A user cannot revoke their only active credential without replacement. Self-service credential change is an atomic rotate operation: the new credential becomes active and the previous credential becomes replaced in one store transaction.

Operators retain explicit revoke/rotate controls.

### 7.4 Deletion semantics

Deletion is a transition to DELETED, not physical removal of the user identity. Historical ownership remains attributable to the deleted UUID. Existing user-owned records are not reassigned or silently erased by M41.

### 7.5 User profile

M41 stores only the existing immutable UUID and lifecycle state. Display name, email, password, avatar, profile metadata, and recovery attributes are deferred.

### 7.6 Authorization

Operator-only commands: create/provision user, disable, reactivate, delete, and administer another user's credentials.

Self-service commands: rotate own credential and inspect own authenticated identity.

Ownership checks remain centralized in the application authorization boundary.

### 7.7 Auditability

M41 introduces a minimal durable management-audit boundary for security-sensitive lifecycle and credential commands. Audit records contain actor identity, action type, target user identity, timestamp, and outcome metadata. Raw credentials and credential hashes are not stored.

Audit querying/UI is deferred.

### 7.8 API and dashboard

M41 exposes management through application capabilities, a thin HTTP transport, and a small dashboard administration/self-service surface. The API never returns a previously issued credential. The dashboard owns presentation only.

### 7.9 Transport semantics

- missing/invalid authentication → 401;
- authenticated non-operator attempting an operator command → 403;
- missing target user → 404;
- invalid lifecycle transition → 409;
- invalid command payload → 400;
- successful credential provisioning/rotation → 200 with the newly issued raw credential exactly once.

## 8. Deferred Decisions

- external identity providers;
- registration/self-service account creation;
- profile fields;
- password/MFA/SSO/recovery;
- richer roles;
- delegated access and organizations;
- audit querying/reporting UI;
- credential expiration policy.


