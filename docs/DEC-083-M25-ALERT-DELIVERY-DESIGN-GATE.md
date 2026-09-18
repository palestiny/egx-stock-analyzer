# DEC-083 — M25 Alert Delivery & Notification Boundary Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M25

## Context

The project now has completed analytical results, immutable historical snapshots, historical comparison and descriptive change detection, plus an AlertCandidate derived from completed analysis.

The current alerting capability intentionally stops at producing an in-process AlertCandidate. It does not deliver notifications, track delivery state, deduplicate repeated delivery, or integrate with a notification provider.

M25 defines the next application/infrastructure boundary: operational notification delivery without moving notification concerns into the analytical pipeline.

## Problem

A generated AlertCandidate is not yet an operational notification.

The system needs explicit answers for:
- when an alert is eligible for delivery;
- what identifies one logical alert event;
- how duplicate delivery is prevented;
- where delivery state is persisted;
- what happens when a provider fails;
- how provider-specific APIs are isolated;
- whether one failed notification blocks others;
- which delivery channel belongs in the MVP;
- whether delivery is synchronous or queued;
- how delivery remains deterministic and testable without a live provider.

## Desired Outcome

Introduce a provider-neutral delivery capability that can:
1. receive an existing AlertCandidate;
2. associate it with one immutable analytical snapshot;
3. create a stable delivery identity;
4. prevent duplicate successful delivery for the same logical event/channel;
5. persist delivery state;
6. call a replaceable notification provider;
7. distinguish successful and failed delivery;
8. keep provider-specific behavior outside application/domain analysis;
9. remain independent from dashboard rendering and analytical scoring.

## Scope

### In scope
- alert-delivery application boundary;
- logical notification-event identity;
- delivery-state persistence boundary;
- idempotency semantics;
- provider abstraction;
- failure isolation;
- synchronous MVP behavior;
- testability and deterministic behavior.

### Explicitly out of scope
- new analytical signals;
- changes to BUY/WATCH/HOLD/AVOID classification;
- alert threshold changes;
- ranking;
- AI-generated alert decisions;
- trading execution;
- multi-user notification preferences;
- distributed queues/workers;
- provider-specific retry/backoff engine;
- notification engagement analytics.

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

The API/dashboard may trigger or display delivery status later, but must not own provider orchestration.

## Existing Gap That Must Be Resolved

The persistence layer already assigns AnalysisResultRecord.snapshot_id, but the current AlertCandidate contains only stock_id and analytical values.

Therefore the stable event identity cannot safely be reconstructed from the current alert object alone.

Before delivery implementation, the application boundary must carry the existing snapshot identity into the alert candidate/projection. This is a contract extension, not a new analytical decision.

The logical event identity is (stock_id, snapshot_id).

A delivery channel is part of the idempotency key: (stock_id, snapshot_id, channel).

## Alternatives Considered

### A — Send from AlertGenerator
Couples domain alert generation to external side effects and makes analysis depend on provider availability.
Decision: Rejected.

### B — Send from API/dashboard
Makes transport own business workflow and prevents clean reuse by scheduled/background execution.
Decision: Rejected.

### C — Dedicated DeliverAlert application capability
Keeps alert generation and delivery separate, reusable, testable, and provider-neutral.
Decision: Preferred.

### D — Queue-first distributed delivery
Provides scalability but introduces infrastructure before the delivery semantics are proven.
Decision: Deferred.

## Proposed Decisions Requiring Acceptance

### 1. Alert Input
Delivery consumes an already-generated AlertCandidate associated with a persisted analytical snapshot. Delivery never recalculates scores or classification.

### 2. Logical Event Identity
The stable logical event is (stock_id, snapshot_id).
The delivery idempotency key is (stock_id, snapshot_id, channel).

### 3. Delivery State
The first MVP persists PENDING, DELIVERED, and FAILED.
A successful delivery is terminal for that event/channel in M25. Retrying a FAILED record is an explicit later delivery operation, not implicit duplicate sending.

### 4. Failure Isolation
Provider failure changes delivery state only. It does not change the analytical result, alert classification, or historical snapshot.
One failed delivery must not erase another successful delivery.

### 5. Provider Boundary
The application depends on a provider-neutral interface.
The first concrete provider/channel should be selected by a separate implementation decision after the boundary is accepted. No provider-specific dependency belongs in the domain.

### 6. Retry Ownership
M25 does not introduce a second generic retry engine.
Provider retry/backoff is deferred. A FAILED delivery is explicitly retryable by a future application operation.

### 7. Execution Model
M25 is synchronous and sequential.
Queue-based delivery and distributed workers are deferred until operational evidence requires them.

### 8. Persistence
Delivery state receives its own persistence boundary. Existing analysis-result persistence is not overloaded with notification lifecycle state.
The delivery store must support lookup by idempotency key and explicit state transitions.

## TDD Acceptance Shape

Implementation must establish at least:
- successful delivery of a new alert event;
- stable event identity uses the analytical snapshot ID;
- duplicate successful delivery is an idempotent no-op;
- already-delivered events do not call the provider again;
- provider failure records FAILED without changing analysis state;
- one failed event does not erase another successful event;
- delivery state survives store recreation;
- provider-specific implementation is hidden behind the provider interface;
- no analytical recalculation occurs during delivery;
- retrying a FAILED event is explicit rather than automatic.

## Design Gate Status

Proposed — implementation is not authorized yet.

Acceptance should explicitly confirm the event identity, the AlertCandidate contract extension, delivery-state boundary, idempotency semantics, provider abstraction, and synchronous MVP.

## Consequences if Accepted

M25 adds an operational delivery boundary around existing alert candidates:

Market Data → Analysis → Classification → Alert Candidate → Delivery

Analysis remains responsible for producing evidence and alert candidates. Delivery infrastructure becomes responsible only for transporting those already-decided candidates.

## Revisit Conditions

Revisit this gate if:
- multiple users require notification preferences;
- queue-based delivery becomes necessary;
- provider rate limits require centralized scheduling;
- delivery analytics become a product requirement;
- notification channels require materially different payload models;
- alert-event identity needs semantics beyond analytical snapshot identity.