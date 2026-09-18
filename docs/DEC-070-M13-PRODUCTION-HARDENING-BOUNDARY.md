# DEC-070 — M13 Production Hardening Boundary and First Slice

**Status:** Accepted  
**Date:** 2026-09-18

## Context

M12 first slice is complete and CI validates the Python test suite, frontend tests, and frontend production build.

The current application is suitable for development and controlled vertical-slice validation, but production operation introduces concerns that are currently only partially addressed:

- runtime health and lifecycle visibility;
- configuration ownership and validation;
- retry behavior and failure diagnostics;
- structured operational logging;
- safe error exposure at the API boundary;
- provider failure handling;
- deployment and recovery procedures;
- security and authentication/authorization;
- persistence and durable historical state;
- operational monitoring.

These concerns must not be solved as one large implementation step.

## Decision

M13 starts with a production-readiness design boundary and a small **Operational Runtime Baseline** slice.

The first M13 implementation slice will establish:

1. explicit application/runtime health semantics;
2. configuration validation at the infrastructure boundary;
3. deterministic startup failure for invalid required configuration;
4. graceful runtime lifecycle behavior;
5. tests for the above behavior;
6. minimal operational diagnostics without exposing internal exception details as an API contract.

The first slice will **not** introduce a database, authentication system, deployment platform, distributed tracing stack, persistent scheduler, or new market-data provider.

## Boundary

The intended direction is:

```
External Environment
        ↓
Configuration / Runtime Boundary
        ↓
Infrastructure Runtime
        ↓
Application
        ↓
Domain
```

Operational concerns should remain outside domain business rules.

## Responsibilities

### Configuration boundary

Owns:

- reading environment/configuration inputs;
- validating infrastructure configuration;
- providing typed configuration to composition.

Does not own:

- analytical rules;
- stock scoring;
- opportunity classification.

### Runtime boundary

Owns:

- lifecycle;
- startup/shutdown;
- infrastructure resource ownership;
- health/readiness information appropriate for the current deployment model.

Does not own:

- business decisions;
- analytical calculations.

### API boundary

Owns:

- HTTP status mapping;
- safe transport errors;
- health endpoint exposure if selected by the implementation slice.

Does not expose:

- provider credentials;
- stack traces;
- internal implementation details as a stable contract.

## First Slice Acceptance Criteria

The first slice is complete when:

- configuration behavior is covered by tests;
- invalid required configuration fails deterministically at composition time;
- runtime lifecycle behavior is covered by tests;
- a minimal health/readiness contract exists if required by the selected runtime model;
- API error responses do not leak raw internal exception details;
- existing analytical behavior remains unchanged;
- the complete Python and frontend CI pipeline remains green;
- documentation records the final contract.

## Deferred M13 Capabilities

These require separate design gates:

- persistent database and migrations;
- authentication and authorization;
- production secret management;
- structured logging schema;
- metrics;
- distributed tracing;
- provider failover;
- persistent job scheduling;
- idempotency;
- durable execution history;
- deployment topology;
- backups and restore;
- rollback strategy;
- performance/load testing;
- rate-limit management;
- security hardening beyond the first API error boundary.

## Trade-offs

Starting with an operational baseline gives deployment and reliability work a concrete boundary without prematurely selecting infrastructure technologies.

The trade-off is that the system will remain development-oriented until persistence, security, observability, and deployment concerns receive their own design gates.

## Revisit Conditions

Revisit this decision when:

- the application is deployed outside local/controlled environments;
- a persistent data store is introduced;
- authentication becomes a requirement;
- scheduled automation must survive process restarts;
- provider reliability requires failover;
- operational SLOs become explicit.
