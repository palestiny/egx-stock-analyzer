# DEC-087 — M28 Automatic Alert Delivery Policy Design Gate

**Status:** Accepted  
**Date:** 2026-09-19  
**Milestone:** M28

## Context

M25 established durable, idempotent alert delivery. M26 added Telegram as a concrete provider. M27 added an explicit single-alert delivery command.

The system can now deliver an alert on request, but it does not define when the platform should automatically deliver alert candidates produced by analysis.

M28 must define automatic delivery as an explicit policy boundary rather than embedding notification side effects inside stock analysis.

## Problem

Define a controlled automatic-delivery capability that can:

1. consume completed analysis outcomes;
2. identify eligible existing alert candidates;
3. request delivery through M25 `DeliverAlert`;
4. preserve per-alert idempotency;
5. isolate delivery failures from analytical execution;
6. remain deterministic and testable;
7. keep provider-specific behavior behind `NotificationProvider`.

## In Scope

- automatic-delivery trigger ownership;
- relationship to configured-market analysis;
- candidate selection boundary;
- per-stock delivery ordering;
- failure isolation;
- interaction with `DeliverAlert`;
- channel configuration;
- aggregate delivery outcome;
- deterministic tests.

## Out of Scope

- new alert-generation rules;
- changing BUY classification;
- provider retries/queues;
- user preferences;
- multi-provider fan-out;
- scheduled delivery policy;
- delivery analytics;
- portfolio/trading behavior;
- AI-based notification decisions.

## Architectural Boundary

```
Completed Market Analysis
        ↓
Automatic Alert Delivery Policy
        ↓
GetAlertCandidate / existing alert projection
        ↓
DeliverAlert
        ↓
NotificationProvider
        ↓
Configured Provider
```

Analysis remains responsible for producing analytical results. Automatic delivery consumes those results and must not modify the analytical pipeline.

## Alternatives

### A. Send notifications directly from RunStockAnalysis

Not selected. This couples stock analysis success to external notification availability and makes provider failures part of the analytical execution path.

### B. Send notifications directly from RunConfiguredMarketAnalysis

Not selected. The configured-market capability owns execution of the universe, not notification policy.

### C. Dedicated automatic-delivery application capability

Preferred candidate. It creates a clear policy boundary around when and how existing alert candidates are delivered.

### D. Scheduler owns automatic notification decisions

Not selected. Scheduler should trigger capabilities, not own business rules for alert eligibility or delivery.

## Open Questions — Must Resolve Before Implementation

1. **Trigger input:** Should automatic delivery consume a completed `Execution`, a symbol list, or persisted completed snapshots?
2. **Candidate eligibility:** Should it deliver only BUY candidates already produced by `GetAlertCandidate`?
3. **Channel:** Should M28 support one configured default channel or an explicit channel set?
4. **Ordering:** Should delivery follow analysis execution order or deterministic symbol order?
5. **Failure semantics:** Should one provider failure continue delivery to other candidates?
6. **Aggregate result:** What states should represent all delivered, mixed, and all failed/no candidates?
7. **Persistence:** Should automatic delivery persist only M25 per-alert records, with no new aggregate delivery table?
8. **Retry:** Should failed delivery remain terminal in M28, preserving M25 semantics?
9. **Trigger coupling:** Should the first MVP be a post-analysis application command rather than an automatic side effect of the analysis use case?
10. **Idempotency:** Should repeated automatic runs rely entirely on M25 snapshot/channel idempotency?

## Proposed Invariants

1. Automatic delivery never changes analytical results.
2. Automatic delivery never recalculates BUY eligibility.
3. Provider failure never marks a successful analysis as failed.
4. One failed notification does not prevent other eligible candidates from being attempted.
5. M25 delivery idempotency remains authoritative.
6. No provider credentials enter application/domain contracts.
7. The first MVP remains synchronous and sequential.
8. No automatic retry is introduced.

## TDD Acceptance Shape

- no eligible candidates produces a deterministic no-op outcome;
- one eligible candidate is delivered through M25;
- multiple candidates are attempted deterministically;
- one delivery failure does not prevent later candidates;
- repeated automatic execution does not create duplicate successful deliveries;
- analysis results remain unchanged;
- provider failures remain delivery failures only;
- no live provider is required by CI.

## Resolved Decisions

### 1. Trigger Input

The MVP consumes a completed market-analysis `Execution`. Only symbols recorded as successful in that execution are considered for automatic delivery.

A partial market-analysis execution is therefore still eligible for delivery of its successful stocks. Failed stock analyses are not candidates for this run.

This keeps automatic delivery downstream of analysis and avoids re-running or rediscovering analysis results.

### 2. Candidate Eligibility

Eligibility is delegated entirely to the existing `GetAlertCandidate` capability.

M28 delivers only candidates already produced by the existing alert-generation boundary. It does not recalculate BUY classification, scores, or thresholds.

### 3. Channel

The MVP uses one configured default delivery channel.

The first configured channel is `telegram`, resolved outside the domain/application policy. M28 does not expose provider-specific configuration as part of the policy contract.

Multiple channels and fan-out are deferred.

### 4. Ordering

Delivery attempts use deterministic normalized-symbol ordering over the successful symbols in the supplied analysis execution.

The existing `Execution` aggregate stores successful symbols as a set, so M28 does not claim to preserve analysis invocation order. Sorting at the delivery boundary provides deterministic behavior without changing the existing execution model.

### 5. Failure Isolation

A delivery failure for one candidate does not prevent later eligible candidates from being attempted.

Automatic delivery therefore has independent per-symbol outcomes and never changes the status of the originating analysis execution.

### 6. Aggregate Delivery Outcome

M28 introduces a delivery-specific aggregate result rather than reusing the analysis `ExecutionState`.

The result states are:

- `COMPLETED` — no delivery failures; this includes the no-eligible-candidates no-op.
- `COMPLETED_WITH_ERRORS` — at least one delivery was attempted and at least one delivery failed.
- `FAILED` — at least one eligible candidate existed and every attempted delivery failed.

The result also reports attempted, delivered, skipped/no-candidate, and failed counts so a no-op is distinguishable from a successful delivery run.

### 7. Persistence

M28 persists only through the existing M25 `AlertDeliveryStore` via `DeliverAlert`.

No aggregate automatic-delivery table or new persistence schema is introduced.

### 8. Retry

M28 does not add automatic retries.

M25 remains authoritative for delivery state, and a failed delivery remains a terminal failed delivery for the MVP. A future explicit retry capability can be introduced by a separate design gate.

### 9. Trigger Coupling

The MVP is an explicit post-analysis application capability.

It is not called from `RunStockAnalysis`, `RunMarketAnalysis`, or the scheduler as an implicit side effect.

A caller may invoke automatic delivery after a completed market-analysis execution. This keeps analysis and notification failure domains independent.

### 10. Idempotency

Repeated automatic delivery runs rely entirely on M25 snapshot/channel idempotency.

An already-delivered candidate returns its existing delivery record and does not produce a duplicate provider send.

## Design Gate Decision

**Status: Accepted — implementation is authorized for the M28 MVP defined here.**

The implementation boundary is:

```
Completed Market Analysis Execution
          ↓
Automatic Alert Delivery Policy
          ↓
GetAlertCandidate
          ↓
DeliverAlert
          ↓
NotificationProvider
          ↓
Configured Provider
```

The automatic-delivery capability owns orchestration and aggregate delivery semantics only. Analytical eligibility, persistence, idempotency, and provider behavior remain owned by the existing boundaries.

## TDD Acceptance Criteria

- no successful analysis symbols produces a deterministic completed no-op;
- one eligible candidate is delivered through `DeliverAlert`;
- multiple eligible candidates are attempted in normalized symbol order;
- one delivery failure does not prevent later candidates;
- no-candidate symbols are skipped without becoming delivery failures;
- repeated execution reuses M25 idempotency and does not send a duplicate already-delivered snapshot/channel;
- analysis execution state and analytical results remain unchanged;
- all eligible deliveries failing produces `FAILED`;
- mixed success/failure produces `COMPLETED_WITH_ERRORS`;
- no live provider is required by CI.

## Revisit Conditions

Revisit when asynchronous delivery, user-specific notification preferences, multiple channels, delivery scheduling, provider retries, or delivery analytics become requirements.
