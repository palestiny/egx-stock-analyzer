# DEC-083 — M24 Alert Delivery & Notification Boundary Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M24

## Context

The project now has immutable analytical results, an `AlertCandidate` derived from completed analysis, historical result snapshots, historical comparison, descriptive historical performance analytics, and API/dashboard presentation.

The current alerting capability stops at producing an in-process `AlertCandidate`. It intentionally does not deliver notifications, track delivery state, deduplicate repeated alerts, or integrate with a notification provider.

The next useful boundary is therefore notification delivery without moving notification concerns into the domain analysis pipeline.

## Problem

A generated alert candidate is not yet an operational notification.

The system needs an explicit application/infrastructure boundary that answers:

- When is an alert eligible for delivery?
- What is the unit of notification identity?
- How are duplicate deliveries prevented?
- Where is delivery state persisted?
- What happens when a provider fails?
- How are provider-specific APIs isolated?
- Does one failed notification block other alerts?
- Which channels belong in the MVP?
- Is delivery synchronous or queued?
- How does the system remain deterministic and testable without a live provider?

## Desired Outcome

Introduce a provider-neutral alert-delivery capability that can:

1. receive an existing `AlertCandidate`;
2. create a stable delivery identity;
3. prevent duplicate delivery for the same logical alert event;
4. persist delivery state;
5. call a replaceable notification provider;
6. distinguish successful and failed delivery;
7. keep provider-specific behavior outside the application/domain layers;
8. remain independent from the dashboard and analytical scoring pipeline.

## Scope

### In scope

- alert-delivery application boundary;
- notification event identity;
- delivery-state persistence boundary;
- duplicate/idempotency semantics;
- provider abstraction;
- failure semantics;
- testability;
- deterministic provider-independent behavior.

### Explicitly out of scope

- adding new analytical signals;
- changing BUY/WATCH/HOLD/AVOID classification;
- changing alert thresholds;
- ranking opportunities;
- AI-generated alert decisions;
- trading execution;
- multi-user notification preferences;
- mobile push infrastructure;
- distributed queues/workers;
- provider-specific retry/backoff implementation;
- analytics about notification engagement.

## Architectural Boundary

```text
Completed Analysis
      ↓
AlertGenerator
      ↓
AlertCandidate
      ↓
Alert Delivery Use Case
      ↓
Notification Delivery Store
      ↓
Notification Provider
```

The dashboard/API may trigger or expose delivery status later, but it must not own provider orchestration.

## Alternatives Considered

### A — Send notifications directly from `AlertGenerator`

**Trade-offs:**

- minimal code;
- but couples domain alert generation to infrastructure;
- makes analysis dependent on external side effects;
- makes deterministic testing harder.

**Decision:** Rejected.

### B — Send notifications from the API/dashboard

**Trade-offs:**

- easy to trigger from a UI request;
- but creates transport-owned business workflow;
- scheduled/background execution cannot reuse it cleanly;
- provider behavior leaks toward the presentation boundary.

**Decision:** Rejected.

### C — Dedicated application delivery use case

Conceptually:

```text
DeliverAlert
    ↓
AlertCandidate
    ↓
Delivery Store + Notification Provider
```

**Trade-offs:**

- explicit responsibility;
- reusable by manual, scheduled, and future automated triggers;
- clean provider boundary;
- introduces a small amount of application infrastructure.

**Decision:** Preferred.

### D — Queue-first distributed delivery

**Trade-offs:**

- stronger scalability and isolation;
- substantially increases infrastructure and operational complexity;
- unnecessary before delivery semantics are established.

**Decision:** Deferred.

## Proposed Decisions Requiring Acceptance

### 1. Alert Candidate Remains the Input

Delivery must consume an already-generated `AlertCandidate`. The delivery layer must not recalculate scores or classification.

### 2. Logical Alert Event Identity

The first MVP should identify an alert event using:

```text
(stock_id, analysis_snapshot_id)
```

This ties a notification to a specific completed analytical snapshot rather than to the current mutable/latest result.

If the current persistence model does not expose a stable snapshot identifier to the alert projection, that missing identity must be introduced at the persistence boundary before delivery implementation.

### 3. Idempotency

A logical alert event may be delivered at most once successfully per configured notification channel.

Repeated delivery attempts for an already-successful event are treated as idempotent no-ops.

### 4. Delivery State

The MVP should persist explicit delivery states:

- PENDING
- DELIVERED
- FAILED

The delivery record must retain enough information to explain the last known outcome without storing provider-specific implementation details in the domain.

### 5. Failure Isolation

Provider failure for one alert must not invalidate the underlying analytical result and must not erase other successfully delivered alerts.

Delivery failure is an operational outcome, not an analytical failure.

### 6. Provider Boundary

The application depends on a provider-neutral interface. Concrete email, webhook, Telegram, or other channel integrations remain infrastructure adapters and are not selected by the domain.

### 7. Retry Ownership

The first MVP does not introduce a second retry engine. Provider-specific transient retry/backoff is deferred until delivery semantics and persistence are stable. A failed delivery remains explicitly retryable through a later application operation.

### 8. Execution Model

The first implementation is synchronous and sequential. Queue-based/asynchronous delivery is deferred until evidence shows the synchronous boundary is insufficient.

## TDD Acceptance Shape

Before implementation is considered complete, tests must cover:

- successful delivery of a new alert event;
- duplicate successful delivery is idempotent;
- provider failure records FAILED without changing analysis state;
- one failed delivery does not erase another successful delivery;
- delivery uses the stable analytical snapshot identity;
- provider-specific implementation is hidden behind the provider boundary;
- repeated execution does not create duplicate successful delivery records;
- already-delivered events are not sent again;
- no analytical recalculation occurs during delivery.

## Consequences

If accepted, M24 adds an operational delivery boundary around the existing alert candidate without changing analytical behavior.

The system remains:

```text
Market Data
   ↓
Analysis
   ↓
Classification
   ↓
Alert Candidate
   ↓
Delivery
```

This preserves the project's principle that analysis produces evidence and candidates, while operational infrastructure decides how those candidates are delivered.

## Revisit Conditions

Revisit this design when:

- multiple users require notification preferences;
- queue-based delivery becomes necessary;
- provider rate limits require centralized scheduling;
- delivery analytics become a product requirement;
- notification channels require materially different payload models;
- alert events need versioned business semantics beyond the analytical snapshot identity.