# DEC-102 — M41 User Management & Credential Administration Design Gate

**Status:** Proposed  
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

## 7. Open Decisions

1. Which administration model should M41 adopt: operator-only, self-service credentials, or full self-service?
2. Who may create the first non-legacy user?
3. Should users be able to revoke their current credential without replacement?
4. What should deletion mean for owned historical records?
5. Should user profile data exist beyond UUID and lifecycle status?
6. Which commands require operator authorization?
7. Which commands require ownership authorization?
8. Should management operations have an audit record in M41?
9. What API surface, if any, should be introduced?
10. What dashboard surface, if any, should be introduced?

## 8. Required Invariants

- user identity remains an immutable internal UUID;
- authentication remains separate from authorization;
- raw credentials remain outside domain entities and durable persistence;
- disabled/deleted users cannot authenticate;
- ownership isolation remains authoritative;
- historical ownership is never silently reassigned;
- operator authorization cannot silently become general user ownership;
- credential lifecycle semantics remain behind CredentialStore;
- management commands remain application capabilities rather than dashboard logic.

## 9. TDD Acceptance Shape

Before implementation, tests should cover the selected management model for:

- user creation/provisioning;
- lifecycle transitions;
- credential administration;
- authorization by operator/owner;
- disabled/deleted authentication behavior;
- historical ownership preservation;
- API error semantics;
- frontend authorization states if a dashboard surface is selected;
- no credential leakage;
- persistence/reload behavior.

## 10. Design Gate Rule

M41 implementation is **not authorized** by this document.

The next step is to select the administration model, resolve the open decisions, record the accepted choice in this document and docs/DECISION_LOG.md, then implement through TDD RED → GREEN on a separate implementation branch.
