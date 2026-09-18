# DEC-085 — M26 External Notification Provider Integration Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M26

## Context

M25 completed the provider-neutral alert-delivery boundary. The system can now take an existing `AlertCandidate`, persist independent delivery state, enforce snapshot-based idempotency, and perform synchronous delivery through a `NotificationProvider` abstraction.

M25 intentionally stopped before connecting the system to an external notification service.

The next architectural question is therefore not how to generate alerts, but how one concrete external delivery adapter should be introduced without leaking provider concerns into the application or changing analytical semantics.

## Problem

The current system has a delivery capability but no production notification transport.

A concrete provider introduces concerns that M25 deliberately kept outside the boundary:

- credentials and secret configuration;
- external network failure;
- provider request/response semantics;
- provider-specific message formatting;
- timeout and retry behavior;
- delivery result mapping;
- rate limits;
- provider availability;
- safe handling of provider errors.

These concerns must remain behind the existing notification-provider boundary.

## Desired Outcome

Introduce one concrete notification provider adapter while preserving:

1. `DeliverAlert` as the application delivery capability;
2. `NotificationProvider` as the replaceable infrastructure boundary;
3. durable delivery-state ownership outside the provider adapter;
4. snapshot-based idempotency;
5. analytical results and alert generation as independent of notification availability;
6. deterministic tests without requiring live external delivery;
7. explicit configuration and secret boundaries.

## Scope

### In scope

- selection of the first concrete provider strategy;
- provider configuration boundary;
- credential/secret handling contract;
- provider request mapping;
- provider response mapping;
- timeout behavior;
- failure classification at the provider boundary;
- test doubles and integration-test boundary;
- application/infrastructure composition;
- operational diagnostics that do not expose credentials.

### Explicitly out of scope

- multiple providers in the first slice;
- notification preferences;
- user-specific subscriptions;
- delivery analytics;
- asynchronous queues/workers;
- distributed delivery;
- scheduled notification policy;
- changing alert-generation rules;
- changing BUY/WATCH/HOLD/AVOID semantics;
- trading execution;
- AI-generated notification decisions.

## Current Boundary

```
AlertCandidate
      ↓
DeliverAlert
      ↓
NotificationProvider
      ↓
Concrete Provider Adapter
      ↓
External Notification Service
```

Delivery-state persistence remains owned by the M25 delivery boundary.

## Alternatives

### A — Email / SMTP

Advantages:
- broadly supported;
- simple conceptual model;
- useful for operational notifications.

Trade-offs:
- SMTP configuration varies;
- sender/domain configuration can be operationally heavier;
- message delivery semantics can be less immediate.

### B — Telegram Bot

Advantages:
- simple message-oriented interaction;
- useful for personal market alerts;
- straightforward provider API model.

Trade-offs:
- bot/token management is provider-specific;
- chat identity/configuration must be supplied;
- external API availability and rate limits become relevant.

### C — Generic Webhook

Advantages:
- provider-neutral consumer integration;
- simple HTTP contract;
- can connect to many downstream automation systems.

Trade-offs:
- does not itself provide a user-facing notification channel;
- recipient semantics become the downstream consumer's responsibility;
- security and endpoint validation require explicit treatment.

### D — Multiple providers immediately

Advantages:
- resilience and flexibility.

Trade-offs:
- multiplies configuration, testing, failure semantics, and operational complexity before there is evidence that multiple providers are needed.

## Proposed MVP Direction

Use exactly one concrete provider adapter first.

The adapter should:

- implement the existing `NotificationProvider` contract;
- receive already-composed alert content rather than analytical domain objects;
- obtain credentials/configuration from infrastructure configuration;
- never persist delivery state itself;
- never decide whether an alert should exist;
- never recalculate scores or classification;
- map provider success/failure into the existing delivery result semantics;
- use explicit network timeouts;
- expose safe diagnostic information without secrets.

The provider choice remains an explicit decision before implementation. No provider-specific code should be merged while this gate is still Proposed.

## Open Questions

1. Which first provider should the MVP support: SMTP email, Telegram Bot, or generic webhook?
2. Should provider credentials come exclusively from environment variables/secrets in the first slice?
3. What provider timeout is appropriate for synchronous delivery?
4. Should transient provider failures be represented only as delivery failure in M26, leaving retry as the existing M25 follow-up, or should one bounded provider retry be included?
5. What exact message payload should be sent, and which alert fields are safe/required?
6. Should provider-specific rate-limit information be retained as diagnostic metadata or only mapped to failure?
7. What integration-test boundary is acceptable without making CI dependent on a live external service?

## Proposed Invariants

1. `DeliverAlert` remains the application owner of delivery semantics.
2. The provider adapter never generates or changes an `AlertCandidate`.
3. Provider credentials never enter domain objects or persisted analytical results.
4. External provider failure must not corrupt or invalidate the underlying analysis.
5. No live provider call is required for deterministic unit tests.
6. The concrete provider remains replaceable behind `NotificationProvider`.
7. M26 does not introduce multi-provider routing or asynchronous infrastructure.

## TDD Acceptance Shape

Before implementation, tests should cover:

- provider request mapping;
- successful provider response;
- provider rejection;
- timeout/network failure;
- safe configuration validation;
- missing credential handling;
- no credential leakage in errors/logs;
- `DeliverAlert` integration with a fake provider;
- idempotency remaining owned by M25 delivery state;
- no analytical recalculation during delivery.

## Design Gate Decision

**Status: Proposed — implementation is not authorized yet.**

The next controlled action is to resolve the provider-selection and configuration questions, then update this document to Accepted before implementing the adapter.

## Revisit Conditions

Revisit this gate if:

- the project requires multiple notification channels;
- asynchronous delivery becomes mandatory;
- user-specific notification preferences become a requirement;
- provider limits require queueing or distributed delivery;
- a concrete provider becomes unavailable;
- security/compliance requirements materially change credential handling.
