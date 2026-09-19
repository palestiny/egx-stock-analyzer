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

## 8. Resolved Decisions

### 1. Security Posture

M37 establishes a **single-operator security boundary**, not a multi-user ownership model.

The current product has one trusted operator and no user-owned resources. Multi-user identity, ownership, organizations, and external identity providers remain future design gates.

### 2. Authentication Mechanism

The MVP uses a **configured bearer operator token**.

The token is supplied through the HTTP `Authorization: Bearer <token>` header. The application does not store passwords, create user accounts, or manage sessions.

This is intentionally the smallest security boundary that protects the current operator controls without prematurely introducing a full identity system.

### 3. Public vs Protected Endpoints

`GET /health` remains public.

All other application/API endpoints are protected by authentication in M37, including read-only analysis, report, alert, history, ranking, opportunity, and workflow endpoints.

This establishes one consistent rule instead of allowing individual endpoints to drift into inconsistent security posture.

### 4. Authorization Model

M37 uses one application-level permission: **operator**.

An authenticated bearer token produces an `OperatorIdentity` carrying the operator permission. Protected application capabilities receive an explicit identity/context object at their boundary.

No role administration or permission database is introduced.

### 5. Identity Representation

The application boundary receives an immutable `AuthenticatedIdentity` value representing the authenticated operator.

The domain remains unaware of authentication. Existing capabilities that do not need identity remain independently callable; protected HTTP/application entry points enforce the identity boundary.

### 6. Authentication vs Authorization Failure Semantics

- Missing or invalid bearer credentials → HTTP **401 Unauthorized**.
- Valid authentication without the required operator permission → HTTP **403 Forbidden**.
- Public health remains HTTP 200 without credentials.
- Authentication errors use generic safe messages and do not reveal token-validation details.

Because the M37 MVP has only one operator permission, 403 is primarily a forward-compatible application authorization contract.

### 7. Credential Lifecycle

The operator token is configured through environment/configuration and is never persisted in the application database.

M37 requires a non-empty token in protected application environments. Rotation is operational: replace the configured token and restart/reload the application.

The token must never appear in API responses, exception messages, logs, dashboard state, or persisted analytical/workflow records.

Token hashing is not introduced because the configured token is treated as an infrastructure secret rather than an application-managed credential record.

### 8. Deterministic Development and CI

Tests use an explicit injected/configured test token and do not contact an external identity service.

Application capabilities are tested directly with deterministic identity objects. HTTP tests cover the authentication adapter/boundary and protected endpoint behavior.

### 9. Migration Path

If the project later needs multiple users or user-owned resources, M37's bearer-token boundary is replaced or extended behind the authentication adapter.

The application identity contract remains the seam for that migration. User ownership is **not** inferred from the current operator token.

### 10. Security Boundary

The intended M37 flow is:

```
HTTP
  ↓
Bearer Token Authentication Adapter
  ↓
AuthenticatedIdentity(operator)
  ↓
Authorization Boundary
  ↓
Application Capability
  ↓
Domain
```

The dashboard must send the configured bearer token but must not implement its own authorization rules.

## 9. Trade-offs

A static operator token is less expressive than user accounts or an external identity provider, but it minimizes security-sensitive application state and keeps the MVP deterministic and provider-neutral.

Protecting all non-health API endpoints gives a simple, auditable rule at the cost of requiring authenticated access even for read-only dashboard data.

The design deliberately accepts operational token rotation rather than introducing password/session lifecycle complexity.

## 10. Invariants

1. Authentication remains outside domain analytical logic.
2. Authorization is enforced at the application/HTTP boundary, not duplicated in dashboard components.
3. HTTP transport does not become the owner of business authorization rules.
4. Protected application capabilities remain callable independently of FastAPI.
5. Credentials and secrets are never returned as API data.
6. Authentication/authorization failures do not expose internal implementation details.
7. Existing analysis semantics do not change because authentication is enabled.
8. Deterministic tests do not depend on live external identity services.
9. Health remains public.
10. M37 does not introduce multi-user ownership semantics.

## 11. TDD Acceptance Shape

Before implementation is complete, tests must establish:

- missing credentials → 401;
- invalid credentials → 401;
- valid operator credentials → protected endpoint succeeds;
- authorization boundary rejects an identity without the required operator permission → 403;
- health remains public;
- identity reaches a protected application capability;
- deterministic test token configuration;
- token is not disclosed in response bodies or safe error messages;
- protected capabilities remain independently testable without FastAPI;
- existing analytical behavior remains unchanged.

## 12. Design Gate Decision

**Status: Accepted — implementation is authorized for the M37 single-operator bearer-token MVP defined above.**

Implementation must use a separate branch and preserve the existing application/domain boundaries.

## 12. Revisit Conditions

Revisit this gate when the product requires multiple users, user-owned data, external identity providers, organization/team permissions, trading authorization, or stronger compliance/security requirements.
