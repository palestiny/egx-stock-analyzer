# DEC-085 — M26 External Notification Provider Integration Design Gate

**Status:** Accepted  
**Date:** 2026-09-19  
**Milestone:** M26

## Context

M25 established provider-neutral alert delivery with durable delivery state, snapshot-based idempotency, and the replaceable `NotificationProvider` boundary. M26 introduces the first concrete external transport without changing analytical or delivery semantics.

## Accepted Decisions

### 1. First Provider

The M26 MVP uses the **Telegram Bot API** as the first concrete notification provider.

The choice fits the current personal market-alert use case: message-oriented delivery over HTTP, with a simple provider contract. SMTP and generic webhook remain future adapters.

### 2. Configuration and Secrets

Telegram configuration is infrastructure-only and comes from environment-backed configuration:

- bot token;
- recipient chat ID.

Credentials never enter domain objects, alert candidates, analytical snapshots, or delivery records. Missing configuration is an explicit configuration error, and secret values must never appear in errors or diagnostics.

### 3. Timeout

The synchronous Telegram request uses an explicit **10-second timeout**.

Timeouts are provider failures and map to the existing M25 `FAILED` delivery state.

### 4. Retry

M26 adds **no automatic provider retry**.

Transient network failures, timeouts, provider rejection, and rate-limit responses map to the existing delivery failure semantics. Retrying FAILED delivery remains a separate future capability.

### 5. Payload

The adapter receives already-composed alert content and maps it to Telegram's message request. It does not recalculate scores, classification, or alert eligibility.

Provider-specific formatting remains inside the adapter.

### 6. Rate Limits and Diagnostics

Provider-specific status information may be retained only as safe diagnostic text. Authorization headers, bot tokens, and other credentials are never exposed.

M26 does not introduce queueing or rate-limit scheduling.

### 7. Testing Boundary

Deterministic tests use an HTTP fake/transport boundary and never require a live Telegram service. Optional live integration testing is explicitly isolated from normal CI and requires externally supplied credentials.

## Architectural Boundary

```
AlertCandidate
      ↓
DeliverAlert
      ↓
NotificationProvider
      ↓
TelegramNotificationProvider
      ↓
Telegram Bot API
```

The provider adapter owns transport mapping only. M25 owns delivery state and idempotency.

## Invariants

1. `DeliverAlert` remains the application owner of delivery semantics.
2. Telegram concepts remain outside the domain and application contracts.
3. Credentials remain infrastructure-only.
4. Provider failure cannot corrupt analysis or historical snapshots.
5. Deterministic unit tests require no live provider.
6. No automatic provider retry is introduced.
7. Replacing Telegram later does not change analytical or delivery-state semantics.

## TDD Acceptance Shape

- configuration is validated safely;
- missing credentials fail deterministically;
- alert payload maps correctly to a Telegram request;
- successful provider response maps to delivery success;
- provider rejection maps to delivery failure;
- timeout/network failure maps to delivery failure;
- secrets never appear in errors or diagnostics;
- `DeliverAlert` remains idempotent;
- provider calls do not recalculate analytical values;
- live external delivery is not required by CI.

## Design Gate Decision

**Status: Accepted — implementation is authorized for the M26 MVP defined here.**

Implementation may proceed with one Telegram adapter behind the existing `NotificationProvider` boundary.

## Revisit Conditions

Revisit this gate if multiple channels are required, asynchronous delivery becomes necessary, provider limits require queueing, user-specific preferences become a product requirement, or security/compliance requirements materially change credential handling.
