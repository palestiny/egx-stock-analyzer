# DEC-086 — M27 Alert Delivery Trigger & Transport Boundary Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M27

## Context

M25 established provider-neutral, durable, idempotent alert delivery through `DeliverAlert`. M26 added the first concrete Telegram provider behind that boundary and composed it into infrastructure when Telegram credentials are configured.

The system now has the capability to deliver an existing `AlertCandidate`, but it does not yet define the application/API boundary through which a caller explicitly requests that delivery.

M27 must define that trigger without moving notification policy into HTTP, duplicating alert generation, or making analysis success depend on notification delivery.

## Problem

Define a controlled application-facing operation that:

1. identifies an existing alert candidate;
2. requests delivery through the existing `DeliverAlert` capability;
3. preserves M25 idempotency and durable delivery state;
4. maps delivery outcomes to a stable transport contract;
5. does not execute fresh analysis;
6. does not recalculate alert eligibility;
7. does not expose provider credentials or provider-specific concepts to API consumers.

## In Scope

- delivery trigger ownership;
- candidate lookup boundary;
- channel selection contract;
- interaction with `GetAlertCandidate`;
- interaction with `DeliverAlert`;
- delivery-result semantics;
- API boundary and error mapping;
- configured-provider absence behavior;
- deterministic tests;
- no-analysis-on-delivery invariant.

## Out of Scope

- new notification providers;
- automatic retries or queues;
- user notification preferences;
- notification scheduling;
- bulk delivery;
- delivery analytics;
- changing alert-generation rules;
- changing M25 delivery-state semantics;
- changing Telegram transport behavior;
- trading execution;
- AI-based notification decisions.

## Architectural Boundary

```
HTTP / Future Trigger
        ↓
DeliverAlertCommand / Application Boundary
        ↓
GetAlertCandidate
        ↓
DeliverAlert
        ↓
NotificationProvider
        ↓
TelegramNotificationProvider
```

The application boundary owns orchestration of an already-existing alert candidate. Provider-specific transport remains infrastructure.

## Alternatives

### A. Add delivery logic directly to the existing alert GET endpoint

Not selected. A GET read endpoint must remain read-only and should not cause an external side effect.

### B. Add a delivery operation directly to `GetAlertCandidate`

Not selected. Candidate retrieval and delivery have different responsibilities and lifecycle semantics.

### C. Dedicated `DeliverAlert` command endpoint/use case

Preferred candidate. It makes the side effect explicit and composes existing M25/M26 capabilities without recalculation.

### D. Trigger delivery from analysis execution automatically

Not selected for M27. Automatic delivery couples analytical execution to external availability and would require new policy decisions around when an alert should be sent.

## Open Questions — Must Resolve Before Implementation

1. **Candidate lookup:** Should the M27 application command accept a complete `AlertCandidate`, or should it resolve the candidate from `symbol` through `GetAlertCandidate`?
2. **Channel selection:** Should the channel be an explicit command field, a configured default, or both?
3. **Missing candidate:** Should no candidate map to a domain/application not-found result or a transport 404?
4. **Provider unavailable:** What stable application result should represent delivery being unconfigured?
5. **Delivery failure:** Should provider failure return the persisted FAILED delivery record or a transport-level error?
6. **Already delivered:** Should idempotent re-delivery return the existing DELIVERED record as a successful command result?
7. **HTTP method:** POST is the candidate because delivery is a side effect; the exact resource shape remains open.
8. **API scope:** Should M27 expose one-symbol delivery only, leaving bulk delivery to a later gate?

## Proposed Invariants

1. Delivery never triggers fresh analysis.
2. Delivery never recalculates BUY eligibility or analytical scores.
3. GET alert remains read-only.
4. M25 idempotency remains authoritative.
5. Provider-specific concepts remain outside application/API contracts.
6. Missing provider configuration is explicit and safe.
7. A delivery failure does not change the alert candidate or analytical snapshot.
8. Repeating a successful delivery request does not create a second external delivery.
9. M27 MVP is single-alert, synchronous, and sequential.

## TDD Acceptance Shape

- candidate is resolved without executing analysis;
- missing candidate is handled explicitly;
- configured channel is delivered through `DeliverAlert`;
- successful delivery returns the persisted delivered state;
- repeated delivery returns the existing delivered state without another provider call;
- provider failure returns persisted failed state;
- provider-unavailable configuration is explicit and safe;
- GET alert remains side-effect free;
- provider-specific error/credential details do not leak through the API;
- deterministic tests require no live Telegram service.

## Accepted Decisions

### 1. Candidate Lookup

The delivery trigger accepts a normalized stock symbol and resolves the current `AlertCandidate` through the existing `GetAlertCandidate` capability.

The trigger does not accept a caller-constructed candidate over HTTP. This keeps candidate construction inside the existing reporting boundary and prevents clients from supplying analytical values or eligibility decisions.

### 2. Channel Selection

The delivery request requires an explicit channel value.

For M27 the supported value is `telegram`. The application boundary remains provider-neutral; Telegram-specific transport behavior stays behind `NotificationProvider`.

No implicit default channel is introduced.

### 3. Missing Candidate

If no alert candidate exists for the requested symbol, the application returns a not-found outcome.

The HTTP transport maps this to **404**.

No provider call is made.

### 4. Provider Unavailable

If delivery is not configured for the requested channel, the application returns a provider-unavailable outcome.

The HTTP transport maps this to **503**. Credentials and provider configuration details are not exposed.

### 5. Delivery Failure

A provider failure is recorded by the existing `DeliverAlert` capability as a durable `FAILED` delivery record.

The command returns that persisted delivery result rather than converting the provider exception into a second application-level failure model.

The HTTP transport returns **200** because the delivery command itself was processed and its terminal delivery outcome is represented explicitly in the response.

### 6. Already Delivered

A repeated request for the same candidate snapshot and channel returns the existing `DELIVERED` record through M25 idempotency.

No second provider call occurs.

The HTTP transport returns **200**.

### 7. HTTP Shape

The M27 MVP uses:

`POST /api/v1/alerts/{symbol}/deliver?channel=telegram`

The operation is explicitly side-effecting. The existing `GET /api/v1/alerts/{symbol}` remains read-only.

### 8. Scope

M27 supports one symbol and one channel per request.

Bulk delivery, multi-channel fan-out, automatic delivery after analysis, queues, retries, scheduling, and user preferences remain deferred.

## Design Gate Decision

**Status: Accepted — implementation is authorized for the M27 MVP defined here.**

The accepted boundary is:

```
POST /api/v1/alerts/{symbol}/deliver
          ↓
GetAlertCandidate
          ↓
DeliverAlert
          ↓
NotificationProvider
          ↓
TelegramNotificationProvider
```

Delivery does not execute analysis, recalculate alert eligibility, or mutate analytical snapshots.

## TDD Acceptance Criteria

- existing alert candidate is resolved by symbol;
- no candidate returns 404 and makes no provider call;
- Telegram delivery uses the explicit `channel=telegram` contract;
- successful delivery returns a delivered record;
- repeated successful delivery returns the same delivered record without a second provider call;
- provider failure is persisted as FAILED and returned as an explicit delivery outcome;
- unconfigured Telegram delivery returns 503 without leaking credentials;
- GET alert remains side-effect free;
- delivery never triggers fresh analysis;
- deterministic tests use a fake provider and do not require live Telegram credentials.

## Revisit Conditions

Revisit this gate if bulk delivery, asynchronous queues, user-specific channels/preferences, scheduled delivery, or automatic delivery policy becomes a requirement.
