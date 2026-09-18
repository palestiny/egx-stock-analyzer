# DEC-084 — M25 Alert Delivery & Notification Boundary Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M25

## Context

The project has completed analysis, historical snapshots, comparison, change detection, and AlertCandidate generation. AlertCandidate currently stops at an in-process candidate and does not deliver notifications or track delivery state.

M25 defines the operational notification boundary without moving notification concerns into the analytical pipeline.

## Problem

The system needs explicit semantics for event identity, duplicate prevention, delivery persistence, provider failure, provider isolation, delivery channel, and synchronous versus queued execution.

## Desired Outcome

Introduce a provider-neutral delivery capability that receives an existing AlertCandidate, associates it with an immutable analysis snapshot, creates a stable delivery identity, persists delivery state, calls a replaceable provider, and isolates delivery failures from analytical state.

## Scope

In scope: delivery application boundary, event identity, delivery-state persistence, idempotency, provider abstraction, failure isolation, synchronous MVP, and deterministic tests.

Out of scope: new analytical signals, classification changes, thresholds, ranking, AI decisions, trading, multi-user preferences, distributed queues, provider retry engines, and engagement analytics.

## Architectural Boundary

Completed Analysis Snapshot
  ↓
GetAlertCandidate
  ↓
AlertCandidate
  ↓
DeliverAlert
  ↓
AlertDeliveryStore
  ↓
NotificationProvider
  ↓
Infrastructure Adapter

API/dashboard may trigger or display delivery status later but must not own provider orchestration.

## Existing Contract Gap

AnalysisResultRecord already has snapshot_id, while AlertCandidate currently contains stock_id and analytical values only. Therefore delivery cannot safely reconstruct stable event identity from the current candidate.

Before delivery implementation, AlertCandidate must carry the existing snapshot identity. This is a projection/contract extension, not a new analytical decision.

Logical event identity: (stock_id, snapshot_id).
Delivery idempotency key: (stock_id, snapshot_id, channel).

## Alternatives

### A — Send from AlertGenerator
Rejected: couples domain alert generation to external side effects.

### B — Send from API/dashboard
Rejected: makes transport own business workflow and prevents clean reuse by scheduled/background execution.

### C — Dedicated DeliverAlert application capability
Preferred: separates generation from delivery, is reusable and testable, and keeps providers replaceable.

### D — Queue-first distributed delivery
Deferred: adds infrastructure before delivery semantics are proven.

## Proposed Decisions Requiring Acceptance

### 1. Alert Input
Delivery consumes an existing AlertCandidate associated with a persisted analysis snapshot. It never recalculates scores or classification.

### 2. Identity
The logical alert event is (stock_id, snapshot_id). The idempotency key is (stock_id, snapshot_id, channel).

### 3. Delivery State
MVP states are PENDING, DELIVERED, and FAILED. Successful delivery is terminal for that event/channel. Retrying FAILED is an explicit later operation.

### 4. Failure Isolation
Provider failure changes delivery state only. It must not alter analysis, classification, or historical snapshots, and must not erase other successful deliveries.

### 5. Provider Boundary
Application code depends on a provider-neutral interface. Concrete channels remain infrastructure adapters.

### 6. Retry Ownership
M25 introduces no second generic retry engine. Provider retry/backoff is deferred.

### 7. Execution Model
M25 is synchronous and sequential. Queue-based delivery is deferred until evidence requires it.

### 8. Persistence
Delivery state gets its own persistence boundary. Analysis-result persistence is not overloaded with notification lifecycle state.

## TDD Acceptance Shape

- new alert event delivers successfully;
- snapshot identity is preserved;
- duplicate successful delivery is an idempotent no-op;
- delivered events do not call the provider again;
- provider failure records FAILED without changing analysis state;
- one failed event does not erase another successful event;
- delivery state survives store recreation;
- provider implementation remains behind its boundary;
- no analytical recalculation occurs during delivery;
- retry of FAILED is explicit rather than automatic.

## Design Gate Status

Proposed — implementation is not authorized yet.

Acceptance must explicitly confirm event identity, AlertCandidate contract extension, delivery-state boundary, idempotency, provider abstraction, and synchronous MVP.

## Revisit Conditions

Revisit if multiple users need notification preferences, queue-based delivery becomes necessary, provider rate limits require centralized scheduling, delivery analytics become a product requirement, channels need materially different payload models, or alert identity needs semantics beyond snapshot identity.