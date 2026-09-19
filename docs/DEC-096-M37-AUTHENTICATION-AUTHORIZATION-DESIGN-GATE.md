# DEC-096 — M37 Authentication & Authorization Boundary Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M37 — Authentication & Authorization Boundary

## 1. Context

M36 introduced an operator-triggered recovery command for persisted scheduled workflow executions:

```
Dashboard
    ↓
POST /api/v1/workflows/executions/{execution_id}/recover
    ↓
RecoverScheduledWorkflowExecution
    ↓
RecoverDurableScheduledWorkflow
```

The project currently has no authentication or authorization boundary. M36 explicitly accepted this limitation because the application has not yet established a multi-user security model.

The system now exposes both read-only operational visibility and a mutating operational control. Before expanding operator controls or exposing the platform to multiple users, the project needs an explicit security boundary.

This gate defines the problem and the decisions that must be resolved before implementation. It does not authorize an authentication implementation.

## 2. Problem

The application currently treats HTTP callers as trusted. That is acceptable for the current local/single-operator development posture but does not establish:

- who the caller is;
- which caller owns or may inspect operational data;
- which caller may trigger mutating workflow controls;
- how credentials are represented and validated;
- how unauthorized and unauthenticated requests are distinguished;
- how authentication state reaches application capabilities without coupling domain logic to HTTP.

Without an explicit boundary, adding more operator actions or user-specific configuration would create inconsistent security behavior.

## 3. Desired Outcome

M37 should define a minimal security architecture that:

1. establishes an explicit authentication boundary;
2. establishes an explicit authorization boundary for protected operations;
3. keeps domain/application business rules independent of HTTP authentication mechanisms;
4. preserves the current application capabilities as reusable use cases;
5. defines safe transport-level failure semantics;
6. defines credential/token lifecycle expectations;
7. remains suitable for a future multi-user product without prematurely introducing distributed identity infrastructure.

## 4. In Scope

- authentication boundary;
- authorization boundary;
- identity representation available to application use cases;
- protected versus public endpoints;
- operator permission semantics;
- credential/token handling contract;
- authentication failure semantics;
- authorization failure semantics;
- application/HTTP dependency direction;
- testing strategy;
- development/test authentication strategy;
- configuration/secrets boundary.

## 5. Out of Scope

- user profile/product UX;
- billing/subscriptions;
- organization/team administration;
- social login;
- password-reset UX;
- MFA;
- SSO;
- external identity-provider selection;
- role/permission administration UI;
- audit-log product design;
- rate limiting;
- WAF/network security;
- distributed session infrastructure;
- authorization of trading operations;
- AI authorization policy.

These may require later design gates.

## 6. Current Security Boundary

Current application flow:

```
HTTP
  ↓
FastAPI
  ↓
Application capabilities
  ↓
Domain
```

There is currently no identity or authorization context in the application boundary.

The intended M37 direction is:

```
HTTP
  ↓
Authentication Adapter / Boundary
  ↓
Authenticated Identity
  ↓
Authorization Boundary
  ↓
Application Capability
  ↓
Domain
```

Authentication-specific details must not leak into domain entities or analytical rules.

## 7. Alternatives

### A. Application-local username/password authentication

Store users and credentials in the application persistence boundary and issue application-managed sessions/tokens.

**Advantages**
- self-contained;
- no external identity dependency;
- straightforward local deployment.

**Trade-offs**
- credential security becomes a first-class responsibility;
- password reset, session lifecycle, and credential migration become application concerns;
- more security-sensitive persistence behavior is introduced.

### B. External identity provider

Delegate identity verification to an established identity provider and accept validated identity claims at the application boundary.

**Advantages**
- avoids storing user passwords;
- mature identity lifecycle options;
- easier path to social login/SSO later.

**Trade-offs**
- external dependency and configuration;
- provider-specific integration complexity;
- local development and deterministic CI require a clear test boundary.

### C. Static API key/operator token

Protect the application with a configured secret token rather than implementing user accounts.

**Advantages**
- minimal implementation;
- suitable for a single trusted operator or internal deployment;
- deterministic and easy to test.

**Trade-offs**
- does not establish user identity;
- weak foundation for multi-user ownership;
- rotation and distribution of shared credentials remain operational concerns.

## 8. Open Questions

1. Is M37 intended to establish a single-operator security boundary first, or a true multi-user identity model?
2. Should the MVP use application-managed credentials, an external identity provider, or a configured operator token?
3. Which endpoints remain public, if any, beyond health?
4. Should read-only analysis/report/history endpoints require authentication?
5. Which mutating operations require an explicit operator permission?
6. What identity representation should application use cases receive?
7. Should authorization be capability-level, role-based, or a minimal operator permission?
8. What are the required credential/token expiration and rotation semantics?
9. Where are secrets configured and how are they prevented from appearing in API responses/logs?
10. What deterministic authentication mechanism should CI and local development use?
11. What HTTP semantics should distinguish unauthenticated from authenticated-but-forbidden callers?
12. What migration path is required if the project later introduces multiple users, ownership, or external identity?

## 9. Invariants

1. Authentication must remain outside domain analytical logic.
2. Authorization must not be implemented by duplicating permission checks across dashboard components.
3. HTTP transport must not become the owner of business authorization rules.
4. Protected application capabilities must remain callable independently of FastAPI.
5. Credentials and secrets must never be returned as API data.
6. Authentication/authorization failures must not expose internal implementation details.
7. Existing analysis semantics must not change because authentication is enabled.
8. Deterministic tests must not depend on live external identity services.
9. Health/readiness semantics must remain explicitly defined after authentication is introduced.
10. M37 must not silently turn existing single-user assumptions into a multi-user data-ownership model without an explicit decision.

## 10. TDD Acceptance Shape

Before implementation is considered complete, tests should establish at least:

- unauthenticated request behavior;
- authenticated request behavior;
- forbidden request behavior;
- protected endpoint coverage;
- public endpoint coverage;
- identity propagation into an application capability;
- authorization enforcement at the application boundary;
- deterministic test credentials/tokens;
- invalid/expired credential behavior;
- secret non-disclosure;
- application capabilities remain independently testable without FastAPI;
- existing analytical behavior remains unchanged.

## 11. Design Gate Decision

**Status: Proposed — implementation is not authorized by this document yet.**

The next action is to resolve the open questions, record the accepted security model, and then create a separate implementation branch.

## 12. Revisit Conditions

Revisit this gate when the product requires multiple users, user-owned data, external identity providers, organization/team permissions, trading authorization, or stronger compliance/security requirements.
