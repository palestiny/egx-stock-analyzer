# M26 — External Notification Provider Integration MVP Completion

**Status:** Complete  
**Date:** 2026-09-19  
**Design Gate:** `docs/DEC-085-M26-EXTERNAL-NOTIFICATION-PROVIDER-DESIGN-GATE.md`  
**Implementation PR:** #41

## Accepted Outcome

M26 added Telegram Bot API as the first concrete provider behind the existing provider-neutral `NotificationProvider` boundary.

The implementation:

- reads Telegram bot token and chat ID from infrastructure configuration;
- keeps credentials outside domain/application delivery records;
- uses an explicit 10-second default request timeout;
- maps provider success and failure into the existing M25 delivery semantics;
- adds no automatic provider retry;
- uses `httpx.MockTransport` for deterministic provider tests;
- composes Telegram delivery only when both required credentials are configured;
- closes the owned HTTP client during infrastructure shutdown.

## Boundary

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

M26 did not change alert generation, analytical calculations, historical snapshots, or M25 idempotency.

## Validation

Focused provider, configuration, and runtime-composition tests were added as part of PR #41.

The merged implementation head is:

`0123e11f63080bba7d34497449b301cb61f90ab1`

The available GitHub workflow-run integration does not currently expose a workflow run for the merge commit, so this completion record does not claim an independently observed CI run for that commit.

## Explicitly Deferred

- delivery trigger/API;
- automatic delivery after analysis;
- multiple providers;
- retries/queues/workers;
- user notification preferences;
- bulk delivery;
- delivery analytics;
- scheduled delivery;
- AI notification decisions.

The next capability requires a separate design gate.
